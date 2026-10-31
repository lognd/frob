//! `frob baseline adopt|prune`: write and shrink `frob-baseline.toml` (rules.md section 6.1.2a).
//!
//! `adopt` is the only writer that adds keys: it runs a full check and records the standing Error
//! findings of one rule as accepted debt, under a reason and a ticket. `prune` removes the keys
//! whose finding no longer occurs. Land runs the same prune on the merge tree.

// frob:ticket 01M66G70CZQMQ6Y55Y5QJPFKV3

use std::path::Path;

use frob_check::{CheckOptions, CheckReport};
use frob_land::baseline_prune::{prune_input, pruned_text};
use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_rules::{BASELINE_FILE, Baseline, BaselineError, Finding, RuleId};
use schemars::JsonSchema;
use serde::Serialize;

use crate::pretty::PrettyExt;
use crate::ticket::{open, resolve};
use crate::workspace::Located;

/// Output of `frob baseline adopt`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BaselineAdoptData {
    /// The rule that was adopted.
    pub rule: String,
    /// Findings recorded as baseline keys.
    pub keys: usize,
    /// The ticket that owns paying the debt down.
    pub ticket: String,
    /// The baseline file written, relative to the repository root.
    pub path: String,
}

/// Output of `frob baseline prune`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BaselinePruneData {
    /// Keys removed because their finding no longer occurs, as `RULE key`.
    pub removed: Vec<String>,
    /// Rules whose table emptied and was deleted.
    pub tables_deleted: Vec<String>,
    /// Whether the file was rewritten (false when it was already minimal or absent).
    pub written: bool,
    /// The baseline file, relative to the repository root.
    pub path: String,
}

/// The flags of `baseline adopt`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct AdoptArgs {
    #[arg(
        required = true,
        value_name = "RULE",
        help = "Rule id to adopt, such as DOC001"
    )]
    rule: String,
    #[arg(long, required = true, help = "Why this debt is accepted")]
    reason: String,
    #[arg(long, required = true, help = "Ticket that owns paying it down")]
    ticket: String,
}

/// The flags of `baseline prune`: none beyond the global ones.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct PruneArgs {}

/// Record the standing Error findings of `RULE` as baselined debt, under a reason and an owning ticket.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "baseline adopt",
    product = "frob",
    exits(ok, refused, usage, internal)
)]
pub struct BaselineAdopt {
    rule: String,
    reason: String,
    ticket: String,
}

/// Remove baseline keys whose finding no longer occurs, judged by one full unscoped check.
#[derive(Debug, Clone, Default, gob_cli::Command)]
#[command(
    verb = "baseline prune",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct BaselinePrune;

/// Add the table for `rule` to the baseline text `existing`, returning the new text and the key count.
///
/// # Errors
/// [`BaselineError`] when the existing text is unreadable or the adoption is refused.
pub fn adopt_text(
    existing: Option<&str>,
    rule: &RuleId,
    reason: &str,
    ticket: &str,
    findings: &[Finding],
) -> Result<(String, usize), BaselineError> {
    let mut baseline = match existing {
        Some(text) => Baseline::parse(text)?,
        None => Baseline::default(),
    };
    let keys = baseline.adopt(rule, reason, ticket, findings)?;
    Ok((baseline.render(), keys))
}

/// One full, unscoped check of the workspace at `root`, as land's head run does it.
fn full_run(ctx: &Context, root: &Path) -> Result<CheckReport, CliError> {
    let ledger = open(ctx)?;
    let options = CheckOptions {
        ledger: Some(ledger.config().clone()),
        clock: Some(ledger.clock().clone()),
        skip_telemetry: true,
        skip_tools: true,
        ..CheckOptions::default()
    };
    tracing::debug!("baseline: running a full unscoped check");
    frob_check::run(root, &options).map_err(CliError::internal)
}

/// The baseline file text at `root`, or `None` when the file does not exist.
fn read_baseline(root: &Path) -> Result<Option<String>, CliError> {
    match std::fs::read_to_string(root.join(BASELINE_FILE)) {
        Ok(text) => Ok(Some(text)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(CliError::internal(e)),
    }
}

/// Write `text` as the baseline file at `root`.
fn write_baseline(root: &Path, text: &str) -> Result<(), CliError> {
    gob_fs::write_atomic(&root.join(BASELINE_FILE), text.as_bytes()).map_err(CliError::internal)
}

impl Command for BaselineAdopt {
    type Data = BaselineAdoptData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<AdoptArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<AdoptArgs>(m)?;
        Ok(Self {
            rule: a.rule,
            reason: a.reason,
            ticket: a.ticket,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<BaselineAdoptData> {
        let rule: RuleId = self
            .rule
            .parse()
            .map_err(|e| CliError::Usage(format!("`{}` is not a rule id: {e}", self.rule)))?;
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let ledger = open(ctx)?;
        let id = resolve(&ledger, &self.ticket)?;
        let handle = ledger
            .show(id)
            .map_err(crate::ticket::cli_err)?
            .summary
            .handle;
        let report = full_run(ctx, &root)?;
        let existing = read_baseline(&root)?;
        let (text, keys) = adopt_text(
            existing.as_deref(),
            &rule,
            &self.reason,
            &handle,
            &report.findings,
        )
        .map_err(|e| CliError::Usage(e.to_string()))?;
        write_baseline(&root, &text)?;
        tracing::info!(rule = %rule, keys, ticket = %handle, "baseline adopt written");
        let rows = vec![format!(
            "adopted {keys} {rule} finding(s) into {BASELINE_FILE} under {handle}"
        )];
        Ok(Payload::new(BaselineAdoptData {
            rule: rule.to_string(),
            keys,
            ticket: handle,
            path: BASELINE_FILE.to_owned(),
        })
        .with_pretty(rows))
    }
}

impl Command for BaselinePrune {
    type Data = BaselinePruneData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<PruneArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        gob_cli::parse::<PruneArgs>(m)?;
        Ok(Self)
    }

    fn run(&self, ctx: &Context) -> Outcome<BaselinePruneData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let Some(existing) = read_baseline(&root)? else {
            tracing::info!("baseline prune: no baseline file");
            return Ok(Payload::new(BaselinePruneData {
                removed: Vec::new(),
                tables_deleted: Vec::new(),
                written: false,
                path: BASELINE_FILE.to_owned(),
            })
            .with_pretty(vec![format!("no {BASELINE_FILE}; nothing to prune")]));
        };
        let report = full_run(ctx, &root)?;
        let input = prune_input(&report);
        let pruned =
            pruned_text(&existing, None, &input).map_err(|e| CliError::Usage(e.to_string()))?;
        let (data, rows) = match pruned {
            None => (
                BaselinePruneData {
                    removed: Vec::new(),
                    tables_deleted: Vec::new(),
                    written: false,
                    path: BASELINE_FILE.to_owned(),
                },
                vec![format!("{BASELINE_FILE} is already minimal")],
            ),
            Some((text, pruned)) => {
                write_baseline(&root, &text)?;
                tracing::info!(
                    removed = pruned.removed.len(),
                    tables_deleted = pruned.tables_deleted.len(),
                    "baseline prune written"
                );
                let rows = vec![format!(
                    "pruned {} key(s) and {} table(s) from {BASELINE_FILE}",
                    pruned.removed.len(),
                    pruned.tables_deleted.len()
                )];
                (
                    BaselinePruneData {
                        removed: pruned
                            .removed
                            .iter()
                            .map(|(rule, key)| format!("{rule} {key}"))
                            .collect(),
                        tables_deleted: pruned.tables_deleted,
                        written: true,
                        path: BASELINE_FILE.to_owned(),
                    },
                    rows,
                )
            }
        };
        Ok(Payload::new(data).with_pretty(rows))
    }
}

/// Register the `baseline` verbs.
pub fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<BaselineAdopt>().register::<BaselinePrune>()
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_rules::Severity;

    fn finding(rule: &str, anchor: &str, sev: Severity) -> Finding {
        Finding::new(rule.parse().unwrap(), sev, None, "msg", anchor)
    }

    // frob:tests crates/frob/src/baseline_cmd.rs::adopt_text
    #[test]
    fn adopt_records_the_rules_error_findings_and_round_trips() {
        let rule: RuleId = "DOC001".parse().unwrap();
        let found = [
            finding("DOC001", "a", Severity::Error),
            finding("DOC001", "b", Severity::Error),
            finding("DOC001", "w", Severity::Unresolved),
            finding("ZED001", "c", Severity::Error),
        ];
        let (text, keys) = adopt_text(None, &rule, "legacy", "~T1", &found).unwrap();
        assert_eq!(keys, 2);
        assert_eq!(Baseline::parse(&text).unwrap().key_count(), 2);
    }

    // frob:tests crates/frob/src/baseline_cmd.rs::adopt_text
    #[test]
    fn adopt_refuses_a_second_adoption_and_a_blank_reason() {
        let rule: RuleId = "DOC001".parse().unwrap();
        let found = [finding("DOC001", "a", Severity::Error)];
        let (text, _) = adopt_text(None, &rule, "legacy", "~T1", &found).unwrap();
        assert!(matches!(
            adopt_text(Some(&text), &rule, "again", "~T1", &found),
            Err(BaselineError::AlreadyAdopted(_))
        ));
        assert!(matches!(
            adopt_text(None, &rule, " ", "~T1", &found),
            Err(BaselineError::Missing { .. })
        ));
    }
}
