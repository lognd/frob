//! `rule catalog`: the std pack rules the project's `[packs]` switches turn on.

// frob:ticket 01M50AQ6XHV6Z8GS0V8J66M9GD

use crunk_check::packs::{self, CatalogRow, PacksSwitch};
use gob_cli::clap::ArgMatches;
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::PRODUCT;

/// One `rule catalog` row: the pack, its family and the rule id.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PackRuleRow {
    /// The pack name.
    pub pack: String,
    /// The family prefix (`A11Y`).
    pub family: String,
    /// The rule id (`A11Y101`).
    pub rule: String,
}

impl From<CatalogRow> for PackRuleRow {
    fn from(r: CatalogRow) -> Self {
        Self {
            pack: r.pack,
            family: r.family,
            rule: r.rule,
        }
    }
}

/// Output of `rule catalog`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct RuleCatalogData {
    /// Pack rules enabled by `[packs]`, in pack order (empty when every pack is off).
    pub packs: Vec<PackRuleRow>,
}

/// List the std pack rules that `[packs]` in crunk.toml switches on.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "rule catalog",
    product = "crunk",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct RuleCatalog;

/// The pack switches a loaded spec declares.
fn switch_of(spec: &crunk_spec::DesignSpec) -> PacksSwitch {
    PacksSwitch {
        crunk_web: spec.packs.crunk_web,
    }
}

impl Command for RuleCatalog {
    type Data = RuleCatalogData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd
    }

    fn from_matches(_: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<RuleCatalogData> {
        let root = gob_product::workspace::locate_root(PRODUCT, &ctx.cwd);
        let spec = crunk_spec::load_spec(&root).map_err(|e| {
            Refusal::new(
                "E-SPEC",
                RefusalClass::GuardNeedsAction,
                &format!("crunk.toml is not a valid design spec: {e}"),
            )
            .with_remedy("fix crunk.toml as described, then rerun")
        })?;
        let rows = packs::catalog(switch_of(&spec)).map_err(|e| {
            Refusal::new(
                "E-PACK",
                RefusalClass::GuardNeedsAction,
                &format!("the crunk-web pack does not build: {e}"),
            )
        })?;
        let packs: Vec<PackRuleRow> = rows.into_iter().map(PackRuleRow::from).collect();
        tracing::info!(rules = packs.len(), "rule catalog built");
        let mut lines: Vec<String> = packs
            .iter()
            .map(|r| format!("{:<10} {:<8} {}", r.pack, r.family, r.rule))
            .collect();
        if lines.is_empty() {
            lines.push("no pack is switched on in [packs]".to_owned());
        }
        Ok(Payload::new(RuleCatalogData { packs }).with_rendered(lines))
    }
}
