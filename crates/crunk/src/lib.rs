//! The `crunk` product: a [`gob_product::Product`] impl on the shared goblin CLI root.
//!
//! [`cli`] assembles the root; `main` only runs it. The generic `check` (the `gob.sibling/1`
//! document) and `doctor` verbs come from `gob-product`; [`doctor`] holds crunk's own report
//! rows, [`tokens`] exports and checks the generated token files, and the built-in `schema` verb
//! comes from `gob-cli`. Every verb but `doctor` and `init` refuse
//! with `E-NO-CONFIG` (exit 3) when no `crunk.toml` exists. No frob crate is linked (the
//! boundary test in `tests/boundary.rs`).

// frob:ticket 01M43ARVS24254G85TMFYH8FGQ
// frob:ticket 01M47QSGHYD2EQ4552V1B4EEQZ
#![expect(
    clippy::disallowed_methods,
    reason = "confinement allow list: path-to-text conversion pending migration to gob-path"
)]

pub mod diff;
pub mod doctor;
pub mod dtcg;
pub mod edit;
pub mod explain;
pub mod export;
pub mod extract;
pub mod fix;
pub mod gallery;
pub mod init;
pub mod map;
pub mod new;
pub mod patch;
pub mod preview;
pub mod query;
pub mod rename;
pub mod review;
pub mod rewrite;
pub mod rule;
pub mod slop_report;
pub mod tokens;

use std::path::Path;

use gob_cli::clap::ArgMatches;
use gob_cli::{Cli, Context, Outcome};
use gob_product::{CheckOptions, Product, ProductRun};
use serde_json::Value;

/// Product name, also the config file stem (`crunk.toml`).
pub const PRODUCT: &str = crunk_check::PRODUCT;

/// crunk as a [`Product`]: the generic `check` and `doctor` plus [`tokens`].
#[derive(Debug, Clone, Copy, Default)]
pub struct CrunkProduct;

gob_product::register_commands!(CrunkProduct);

// frob:ticket 01M4FD0EP322SV5ZNXD5SQT8RX
gob_cli::inventory::submit! {
    gob_cli::SchemaExtension::new(crunk_spec::schema::schema)
}

/// The crunk-only `check --gate` and `check --report` flags.
#[derive(Debug, Clone, gob_cli::clap::Args)]
#[command(about = None, long_about = None)]
struct GateArgs {
    #[arg(
        long,
        value_name = "GATE",
        value_parser = ["check", "release"],
        help = "Judge for this gate; release raises stale human reviews to errors"
    )]
    gate: Option<String>,
    // frob:ticket 01M4CXTBPEVSYD93X6S90ZRDZ9
    #[arg(
        long,
        value_name = "REPORT",
        value_parser = ["slop"],
        help = "Add a named report to the document; slop lists every signal with its evidence and tier"
    )]
    report: Option<String>,
    // frob:ticket ~NGXAEYS
    #[arg(
        long,
        value_name = "TIER",
        value_parser = ["T0", "T1", "T2", "T3", "T4"],
        default_value = "T1",
        help = "Run rules up to this tier; rules above it are listed under not_run, never clean"
    )]
    tier: String,
}

/// The `--tier` choice as a [`crunk_check::Tier`]; the value parser has already vetted it.
fn parse_tier(args: Option<&GateArgs>) -> crunk_check::Tier {
    args.and_then(|a| a.tier.parse().ok()).unwrap_or_default()
}

impl Product for CrunkProduct {
    const NAME: &'static str = PRODUCT;
    const VERSION: &'static str = env!("CARGO_PKG_VERSION");
    const DOCTOR_SUMMARY: &'static str =
        "Report the crunk version, the repository root and the state of crunk.toml.";
    const REQUIRES_CONFIG: bool = true;
    const NO_CONFIG_VERBS: &'static [&'static str] = &["init"];

    type CheckData = Value;
    type Doctor = doctor::DoctorData;

    fn has_config(root: &Path) -> bool {
        crunk_check::has_config(root)
    }

    fn check(
        ctx: &Context,
        root: &Path,
        opts: &CheckOptions,
        matches: &ArgMatches,
    ) -> Outcome<Value> {
        // frob:ticket 01M4CXTBPEVSYD93X6S90ZRDZ9
        let gate_args = gob_cli::parse::<GateArgs>(matches).ok();
        let tier = parse_tier(gate_args.as_ref());
        tracing::debug!(%tier, "crunk check tier");
        let slop = gate_args
            .as_ref()
            .and_then(|a| a.report.as_deref())
            .is_some_and(|r| r == "slop");
        let only = if slop {
            vec![slop_report::FAMILY.to_owned()]
        } else {
            opts.only.clone()
        };
        let run = crunk_check::run_to_tier(
            root,
            &crunk_check::CheckOptions {
                only,
                fail_on: opts.fail_on,
                base: opts.base.clone(),
                ticket_scope: opts.ticket_scope.clone(),
                // frob:ticket 01M4CXSM408E7A05DWKENDB7V4
                gate: match gob_cli::parse::<GateArgs>(matches)
                    .ok()
                    .and_then(|a| a.gate)
                    .as_deref()
                {
                    Some("release") => crunk_rules::family::Gate::Release,
                    _ => crunk_rules::family::Gate::Check,
                },
            },
            tier,
        )
        .map(|run| {
            let mut document = crunk_check::sibling_document(&run);
            if slop {
                let entries =
                    crunk_rules::registry::entries(crunk_check::product_rules::RULE_INDEXES);
                document["slop_report"] = slop_report::build(&run, &entries);
            }
            ProductRun {
                report: run.report,
                document,
                warnings: run.warnings,
            }
        });
        gob_product::sibling_check(Self::NAME, ctx, run)
    }

    // frob:ticket 01M4CXSM408E7A05DWKENDB7V4
    fn configure_check(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<GateArgs>(gob_product::shared_flags(cmd))
    }

    fn doctor(_ctx: &Context, root: &Path, _matches: &ArgMatches) -> Outcome<doctor::DoctorData> {
        Ok(doctor::report(root))
    }

    fn register(cli: Cli) -> Cli {
        cli.register::<tokens::Tokens>()
            .register::<review::Review>()
            .register::<review::Ack>()
            .register::<query::Query>()
            .register::<map::Map>()
            .register::<explain::Explain>()
            .register::<rule::RuleCatalog>()
            .register::<preview::Preview>()
            .register::<diff::Diff>()
            .register::<init::Init>()
            .register::<fix::Fix>()
            .register::<gallery::GalleryCheck>()
            .register::<gallery::GalleryEnumerate>()
            .register::<gallery::GalleryRender>()
            .register::<gallery::GalleryTriage>()
            .register::<dtcg::ImportDtcg>()
            .register::<dtcg::ExportDtcg>()
            .register::<export::ExportCss>()
            .register::<export::ExportTailwind>()
            .register::<export::ExportUss>()
            .register::<export::ExportCsharp>()
            .register::<rename::Rename>()
            .register::<edit::Edit>()
            .register::<new::New>()
            .register::<extract::ExtractToken>()
    }
}

/// The fully registered `crunk` command-line root.
pub fn cli() -> Cli {
    gob_product::cli::<CrunkProduct>()
}

#[cfg(test)]
mod tier_tests {
    use super::cli;
    use gob_cli::run_for_test;
    use serde_json::Value;
    use std::path::Path;

    fn project() -> tempfile::TempDir {
        let dir = tempfile::tempdir().expect("tempdir");
        let spec = crunk_spec::presets::preset("default").expect("default preset");
        std::fs::write(dir.path().join("crunk.toml"), spec).expect("write config");
        dir
    }

    /// Exit code, parsed stdout and stdout plus stderr text.
    fn check(dir: &Path, extra: &[&str]) -> (i32, Value, String) {
        let mut args = vec!["check", "--json"];
        args.extend_from_slice(extra);
        let (code, out, err) = run_for_test(&cli(), &args, dir);
        (
            code,
            serde_json::from_str(&out).unwrap_or(Value::Null),
            format!("{out}{err}"),
        )
    }

    // frob:tests crates/crunk/src/lib.rs::CrunkProduct
    #[test]
    fn tier_defaults_to_t1() {
        let dir = project();
        let (_, env, _) = check(dir.path(), &[]);
        assert_eq!(env["data"]["not_run"]["tier"], "T1", "{env}");
    }

    // frob:tests crates/crunk/src/lib.rs::CrunkProduct
    #[test]
    fn a_valid_tier_is_passed_through() {
        let dir = project();
        let (_, env, _) = check(dir.path(), &["--tier", "T0"]);
        assert_eq!(env["data"]["not_run"]["tier"], "T0", "{env}");
    }

    // frob:tests crates/crunk/src/lib.rs::CrunkProduct
    #[test]
    fn an_invalid_tier_exits_two_listing_the_choices() {
        let dir = project();
        let (code, _, err) = check(dir.path(), &["--tier", "T9"]);
        assert_eq!(code, 2, "{err}");
        assert!(err.contains("T0") && err.contains("T4"), "{err}");
    }
}
