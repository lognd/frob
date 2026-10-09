//! The `check` verb: flags in, [`crate::run`] out, exit code from `fail_on`.

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{
    Cli, CliError, Command, CommandMeta, Context, Described, ExitCode, FindingsFailure, Outcome,
    Payload, Refusal, RefusalClass,
};
use gob_diagnostics::{FindingRecord, MemorySources};
use std::collections::{BTreeMap, BTreeSet};

use gob_rules::{Finding, Registry, Severity};
use gob_text::SourceText;
use schemars::JsonSchema;
use serde::Serialize;

use gob_check::{CheckError, CheckReport, Counts, FailOn, FixOutcome, StageTime, Stats};

use crate::options::CheckOptions;
use crate::run_with_diff;

/// Adds the `check` verb to a product root.
pub fn register(cli: Cli) -> Cli {
    cli.register::<Check>()
}

/// The rule page of `--explain`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct Explained {
    /// Rule id.
    pub id: String,
    /// Kebab-case slug.
    pub slug: String,
    /// Default severity.
    pub severity: String,
    /// One-line summary.
    pub summary: String,
    /// The full explanation text.
    pub explanation: String,
}

/// The timing breakdown of `--timing` and `-v`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TimingView {
    /// Stages in execution order; tool stages come last and are not budgeted.
    pub stages: Vec<StageTime>,
    /// Milliseconds in budgeted (built-in) stages.
    pub budget_ms: u64,
    /// Milliseconds in tool stages, outside the budget.
    pub tools_ms: u64,
}

/// Output of `check`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CheckData {
    /// Findings by severity.
    pub counts: Counts,
    /// Findings an exception suppressed.
    pub suppressed: usize,
    /// One line per finding: `file:line:col: severity RULE message`.
    pub lines: Vec<String>,
    /// `--ticket` text view only: one count line per rule for the findings outside the ticket diff.
    pub elsewhere: Vec<String>,
    /// The findings as structured records (filled in JSON mode only).
    pub findings: Vec<FindingRecord>,
    /// Counters of the run.
    pub stats: Option<Stats>,
    /// Stage timing, present with `--timing` or `-v`.
    pub timing: Option<TimingView>,
    /// Per-language fidelity accounting (files examined, `NotApplicable` per family, Unresolved).
    pub fidelity: Option<gob_check::FidelityReport>,
    /// Where each configured sibling binary was found (D87); text view only under `-v`.
    pub siblings: Vec<gob_check::SiblingRow>,
    /// `-v` text view: one line per sibling.
    pub sibling_lines: Vec<String>,
    /// What `--fix` did, present with `--fix`.
    pub fix: Option<FixOutcome>,
    /// The ticket the run was scoped to.
    pub ticket: Option<String>,
    /// The failing threshold in force.
    pub fail_on: Option<String>,
    /// Unresolved findings carrying a required reason.
    pub required_unresolved: usize,
    /// Rules that could not be evaluated (each one a required Unresolved `evaluation-failed` finding).
    pub not_evaluated: usize,
    /// The Unresolved gate in force (`required`, `never` or `all`).
    pub fail_on_unresolved: Option<String>,
    /// Non-fatal notes.
    pub notes: Vec<String>,
    /// The rule page, present with `--explain`.
    pub explain: Option<Explained>,
}

impl CheckData {
    fn empty() -> Self {
        Self {
            counts: Counts::default(),
            suppressed: 0,
            lines: Vec::new(),
            elsewhere: Vec::new(),
            findings: Vec::new(),
            stats: None,
            timing: None,
            fidelity: None,
            siblings: Vec::new(),
            sibling_lines: Vec::new(),
            fix: None,
            ticket: None,
            fail_on: None,
            required_unresolved: 0,
            not_evaluated: 0,
            fail_on_unresolved: None,
            notes: Vec::new(),
            explain: None,
        }
    }
}

/// One-line summary of `frob check` (the generic verb's metadata).
pub const CHECK_SUMMARY: &str =
    "Run the rules over the repository and report findings; exit 1 at or above `fail_on`.";

// frob:ticket 01M47QSHBWSGEYXJ56PR6FQBS9
/// The flags and run behind `frob check`; the binary runs it through the generic `gob-product` verb.
#[derive(Debug, Clone)]
pub struct Check {
    ticket: Option<String>,
    only: Vec<String>,
    fix: bool,
    fail_on: Option<FailOn>,
    explain: Option<String>,
    timing: bool,
    base: Option<String>,
}

fn fail_on_name(f: FailOn) -> &'static str {
    match f {
        FailOn::None => "none",
        FailOn::Advisory => "advisory",
        FailOn::Warn => "warn",
        FailOn::Error => "error",
    }
}

/// `file:line:col` resolver over the files the findings point into.
fn sources_of(root: &std::path::Path, report: &CheckReport) -> MemorySources {
    let mut sources = MemorySources::new();
    let mut seen = std::collections::HashSet::new();
    for f in &report.findings {
        let Some(span) = f.span else { continue };
        if !seen.insert(span.file) {
            continue;
        }
        let Some(path) = report.files.path(span.file) else {
            continue;
        };
        if let Ok(text) = std::fs::read_to_string(root.join(path))
            && let Ok(src) = SourceText::new(text)
        {
            sources.insert(span.file, path, src);
        }
    }
    sources
}

fn line_of(record: &FindingRecord) -> String {
    let line = base_line(record);
    match &record.required {
        Some(reason) => format!("{line} [required: {reason}]"),
        None => line,
    }
}

fn base_line(record: &FindingRecord) -> String {
    match (&record.file, record.line, record.column) {
        (Some(file), Some(line), Some(col)) => format!(
            "{file}:{line}:{col}: {} {} {}",
            record.severity, record.rule, record.message
        ),
        (Some(file), _, _) => format!(
            "{file}: {} {} {}",
            record.severity, record.rule, record.message
        ),
        _ => format!("{} {} {}", record.severity, record.rule, record.message),
    }
}

fn refusal(code: &str, class: RefusalClass, err: &CheckError, remedy: &str) -> CliError {
    Refusal::new(code, class, err.to_string())
        .with_remedy(remedy)
        .into()
}

/// Map a pipeline failure onto the exit table (cli.md section 2).
fn cli_error(err: CheckError) -> CliError {
    match err {
        CheckError::UnknownFamily(_) | CheckError::FixNeedsScope | CheckError::Ticket(_) => {
            CliError::Usage(err.to_string())
        }
        CheckError::Config(_) => refusal(
            "E-CONFIG",
            RefusalClass::GuardNeedsAction,
            &err,
            "fix frob.toml as described, then rerun",
        ),
        CheckError::NoLedger(_) => refusal(
            "E-CHECK-NO-LEDGER",
            RefusalClass::GuardNeedsAction,
            &err,
            "run inside the repository that holds the ticket ledger",
        ),
        CheckError::Lock(_) => refusal(
            "E-CHECK-LOCK",
            RefusalClass::GuardNeedsAction,
            &err,
            "repair frob.lock or regenerate it with `frob ack --all`",
        ),
        CheckError::FixStale(_) => refusal(
            "E-FIX-STALE",
            RefusalClass::GuardNeedsAction,
            &err,
            "rerun `frob check`, then `frob check --fix`",
        ),
        CheckError::Walk(_) | CheckError::FixIo(_) => CliError::internal(err),
    }
}

impl Described for Check {
    const META: CommandMeta = CommandMeta {
        verb: "check",
        product: "frob",
        idempotent: false,
        dry_run: false,
        exits: &[
            ExitCode::Ok,
            ExitCode::Negative,
            ExitCode::Usage,
            ExitCode::Refused,
            ExitCode::Internal,
        ],
        summary: CHECK_SUMMARY,
        module: module_path!(),
        deprecated: None,
        markdown: false,
    };
}

impl Command for Check {
    type Data = CheckData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("ticket")
                .long("ticket")
                .value_name("HANDLE")
                .help("Scope per-file rules to the ticket's lease files plus [check] ticket_hops of dependents"),
        )
        .arg(
            Arg::new("only")
                .long("only")
                .value_name("FAMILY")
                .value_delimiter(',')
                .action(ArgAction::Append)
                .help("Keep only these rule families or ids (comma separated)"),
        )
        .arg(
            Arg::new("fix")
                .long("fix")
                .action(ArgAction::SetTrue)
                .help("Apply Deterministic fixes, then re-run once"),
        )
        .arg(
            Arg::new("fail_on")
                .long("fail-on")
                .value_name("SEVERITY")
                .value_parser(["error", "warn", "advisory", "none"])
                .help("Exit 1 at or above this severity (default: [check] fail_on)"),
        )
        .arg(
            Arg::new("explain")
                .long("explain")
                .value_name("RULEID")
                .help("Print the rule page and exit 0"),
        )
        .arg(
            Arg::new("timing")
                .long("timing")
                .action(ArgAction::SetTrue)
                .help("Print the per-stage timing breakdown"),
        )
        .arg(
            Arg::new("base")
                .long("base")
                .value_name("REF")
                .help("Ref the --ticket diff is taken against (default: [check] base)"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            ticket: m.get_one::<String>("ticket").cloned(),
            only: m
                .get_many::<String>("only")
                .map(|v| v.cloned().collect())
                .unwrap_or_default(),
            fix: m.get_flag("fix"),
            fail_on: m
                .get_one::<String>("fail_on")
                .and_then(|s| FailOn::parse(s)),
            explain: m.get_one::<String>("explain").cloned(),
            timing: m.get_flag("timing"),
            base: m.get_one::<String>("base").cloned(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<CheckData> {
        if let Some(id) = &self.explain {
            return explain(id);
        }
        let root = gob_git::Repo::discover(&ctx.cwd)
            .ok()
            .and_then(|r| r.work_dir().map(std::path::Path::to_path_buf))
            .unwrap_or_else(|| ctx.cwd.clone());
        let opts = CheckOptions {
            ticket: self.ticket.clone(),
            only: self.only.clone(),
            fix: self.fix,
            fail_on: self.fail_on,
            base: self.base.clone(),
            clock: Some(ctx.clock.clone()),
            ..CheckOptions::default()
        };
        let (report, diff) = run_with_diff(&root, &opts).map_err(cli_error)?;
        let lead = (!ctx.json && ctx.verbosity == 0)
            .then_some(diff.as_ref())
            .flatten();
        let data = data_of(
            &root,
            &report,
            ctx.json,
            self.timing || ctx.verbosity > 0,
            lead,
        );
        if report.exit_code() == ExitCode::Negative {
            let c = data.counts;
            let summary = format!(
                "{} error(s), {} warning(s), {} advisory at or above `{}`; {} unresolved ({} required, gate `{}`)",
                c.error,
                c.warn,
                c.advisory,
                fail_on_name(report.fail_on),
                c.unresolved,
                data.required_unresolved,
                report.fail_on_unresolved.name(),
            );
            let detail = data
                .lines
                .iter()
                .chain(&data.elsewhere)
                .cloned()
                .collect::<Vec<_>>()
                .join("\n");
            let findings = data.findings.clone();
            let data = serde_json::to_value(&data).map_err(CliError::internal)?;
            return Err(CliError::Findings(Box::new(FindingsFailure {
                summary,
                detail,
                data,
                findings,
                warnings: report.warnings,
            })));
        }
        let mut payload = Payload::new(data);
        payload.warnings = report.warnings;
        Ok(payload)
    }
}

// frob:ticket 01M413V8CDKKBSBV8JDV92VDGB
/// Rules whose findings always print in full under `--ticket`: they judge the diff itself.
const DIFF_RULES: [&str; 2] = ["SCOPE001", "TICK002"];

/// True when `finding` must print in full although its path is outside the ticket diff.
///
/// Anything that can fail the gate stays visible: errors, required unresolved
/// findings, and everything at or above `fail_on`.
fn blocking(report: &CheckReport, finding: &Finding) -> bool {
    finding.severity == Severity::Error
        || finding.required.is_some()
        || report
            .fail_on
            .threshold()
            .is_some_and(|t| finding.severity >= t && finding.severity != Severity::Unresolved)
}

/// Split the report lines into the full lines and one count line per `(rule, severity)` for the rest.
///
/// A finding is full when its file is in `diff`, its rule judges the diff, or it is [`blocking`].
fn lead_lines(
    report: &CheckReport,
    records: &[FindingRecord],
    diff: &BTreeSet<String>,
) -> (Vec<String>, Vec<String>) {
    let mut full = Vec::new();
    let mut counts: BTreeMap<(String, String), usize> = BTreeMap::new();
    for (finding, record) in report.findings.iter().zip(records) {
        let in_diff = record.file.as_deref().is_some_and(|f| diff.contains(f));
        if in_diff || DIFF_RULES.contains(&record.rule.as_str()) || blocking(report, finding) {
            full.push(line_of(record));
        } else {
            *counts
                .entry((record.rule.clone(), record.severity.clone()))
                .or_default() += 1;
        }
    }
    let total: usize = counts.values().sum();
    tracing::debug!(
        full = full.len(),
        elsewhere = total,
        "ticket diff partition"
    );
    let mut summary = Vec::new();
    if total > 0 {
        summary.push(format!(
            "{total} more finding(s) outside this ticket's diff (rerun with -v to list them, or --json):"
        ));
        summary.extend(
            counts
                .into_iter()
                .map(|((rule, sev), n)| format!("  {rule} {sev} x{n}")),
        );
    }
    (full, summary)
}

/// `grimble: beside-frob /path (version)`, one sibling for the `-v` text view.
fn sibling_line(row: &gob_check::SiblingRow) -> String {
    format!(
        "sibling {}: {}{}{}",
        row.product,
        row.location,
        row.path
            .as_deref()
            .map_or_else(String::new, |p| format!(" {p}")),
        row.version
            .as_deref()
            .map_or_else(String::new, |v| format!(" ({v})")),
    )
}

/// Build the verb data of `report`; `lead` is the ticket diff when the text view should lead with it.
fn data_of(
    root: &std::path::Path,
    report: &CheckReport,
    json: bool,
    with_timing: bool,
    lead: Option<&BTreeSet<String>>,
) -> CheckData {
    let sources = sources_of(root, report);
    let registry = Registry::global();
    let records: Vec<FindingRecord> = report
        .findings
        .iter()
        .map(|f: &Finding| {
            let mut record = FindingRecord::from_finding(f, &sources, registry);
            record.fingerprint = report.fingerprint_of(f);
            record
        })
        .collect();
    let (lines, elsewhere) = match lead {
        Some(diff) => lead_lines(report, &records, diff),
        None => (records.iter().map(line_of).collect(), Vec::new()),
    };
    CheckData {
        counts: Counts::of(&report.findings),
        suppressed: report.suppressed.len(),
        lines,
        elsewhere,
        findings: if json { records } else { Vec::new() },
        stats: Some(report.stats),
        timing: with_timing.then(|| crate::verb::TimingView {
            stages: report.timing.stages.clone(),
            budget_ms: report.timing.budget_ms(),
            tools_ms: report.timing.tools_ms(),
        }),
        fidelity: Some(report.fidelity.clone()),
        siblings: if json || with_timing {
            report.siblings.clone()
        } else {
            Vec::new()
        },
        sibling_lines: if json || !with_timing {
            Vec::new()
        } else {
            report.siblings.iter().map(sibling_line).collect()
        },
        fix: report.fix.clone(),
        ticket: report.scope.clone(),
        fail_on: Some(fail_on_name(report.fail_on).to_owned()),
        required_unresolved: report.required_unresolved(),
        not_evaluated: report
            .findings
            .iter()
            .filter(|f| {
                matches!(
                    f.required,
                    Some(gob_rules::RequiredReason::EvaluationFailed { .. })
                )
            })
            .count(),
        fail_on_unresolved: Some(report.fail_on_unresolved.name().to_owned()),
        notes: Vec::new(),
        explain: None,
    }
}

/// `--explain`: the registry's page for one rule.
fn explain(id: &str) -> Outcome<CheckData> {
    let wanted = id.trim().to_ascii_uppercase();
    let meta = Registry::global()
        .by_id(&wanted)
        .or_else(|| Registry::global().by_slug(id.trim()))
        .ok_or_else(|| CliError::Usage(format!("no rule `{id}`; see docs/reference/rules")))?;
    let mut data = CheckData::empty();
    data.explain = Some(Explained {
        id: meta.id.to_owned(),
        slug: meta.slug.to_owned(),
        severity: format!("{:?}", meta.severity).to_ascii_lowercase(),
        summary: meta.summary.to_owned(),
        explanation: meta.explanation.to_owned(),
    });
    Ok(Payload::new(data))
}

#[cfg(test)]
mod tests {
    use super::*;
    use gob_diagnostics::EnvelopeError;

    // frob:tests crates/frob-check/src/verb.rs::cli_error
    #[test]
    fn a_stale_fix_is_a_guard_refusal_with_its_own_code_and_a_remedy() {
        let err = cli_error(CheckError::FixStale("a.txt".to_owned()));
        assert_eq!(err.exit_code(), ExitCode::Refused);
        let CliError::Refusal(refusal) = err else {
            panic!("expected a refusal, got {err}");
        };
        let envelope = EnvelopeError::from(&refusal);
        assert_eq!(envelope.code, "E-FIX-STALE");
        assert!(!envelope.retryable);
        assert!(envelope.message.contains("a.txt"), "{}", envelope.message);
        assert_eq!(
            envelope.remedy.as_deref(),
            Some("rerun `frob check`, then `frob check --fix`")
        );
    }
}
