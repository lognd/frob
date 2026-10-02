//! The `check` verb: flags in, [`crate::run`] out, exit code from `fail_on`.

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{Cli, CliError, Command, Context, ExitCode, Outcome, Payload, Refusal, RefusalClass};
use gob_diagnostics::{FindingRecord, MemorySources};
use gob_rules::{Finding, Registry};
use gob_text::SourceText;
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FailOn;
use crate::error::CheckError;
use crate::options::CheckOptions;
use crate::pipeline::run;
use crate::report::{CheckReport, Counts, FixOutcome, StageTime, Stats};

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
    /// The findings as structured records (filled in JSON mode only).
    pub findings: Vec<FindingRecord>,
    /// Counters of the run.
    pub stats: Option<Stats>,
    /// Stage timing, present with `--timing` or `-v`.
    pub timing: Option<TimingView>,
    /// What `--fix` did, present with `--fix`.
    pub fix: Option<FixOutcome>,
    /// The ticket the run was scoped to.
    pub ticket: Option<String>,
    /// The failing threshold in force.
    pub fail_on: Option<String>,
    /// Unresolved findings carrying a required reason.
    pub required_unresolved: usize,
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
            findings: Vec::new(),
            stats: None,
            timing: None,
            fix: None,
            ticket: None,
            fail_on: None,
            required_unresolved: 0,
            fail_on_unresolved: None,
            notes: Vec::new(),
            explain: None,
        }
    }
}

/// Run the rules over the repository and report findings; exit 1 at or above `fail_on`.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "check",
    product = "frob",
    exits(ok, negative, usage, refused, internal)
)]
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
        CheckError::Walk(_) | CheckError::FixIo(_) => CliError::internal(err),
    }
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
            ..CheckOptions::default()
        };
        let report = run(&root, &opts).map_err(cli_error)?;
        let data = data_of(&root, &report, ctx.json, self.timing || ctx.verbosity > 0);
        if report.exit_code() == ExitCode::Negative {
            let c = data.counts;
            return Err(CliError::Negative(format!(
                "{} error(s), {} warning(s), {} advisory at or above `{}`; {} unresolved ({} required, gate `{}`):\n{}",
                c.error,
                c.warn,
                c.advisory,
                fail_on_name(report.fail_on),
                c.unresolved,
                data.required_unresolved,
                report.fail_on_unresolved.name(),
                data.lines.join("\n")
            )));
        }
        let mut payload = Payload::new(data);
        payload.warnings = report.warnings;
        Ok(payload)
    }
}

/// Build the verb data of `report`.
fn data_of(
    root: &std::path::Path,
    report: &CheckReport,
    json: bool,
    with_timing: bool,
) -> CheckData {
    let sources = sources_of(root, report);
    let registry = Registry::global();
    let records: Vec<FindingRecord> = report
        .findings
        .iter()
        .map(|f: &Finding| {
            FindingRecord::from_finding(f, &sources, registry)
                .with_required(report.required.get(f).cloned())
        })
        .collect();
    CheckData {
        counts: Counts::of(&report.findings),
        suppressed: report.suppressed.len(),
        lines: records.iter().map(line_of).collect(),
        findings: if json { records } else { Vec::new() },
        stats: Some(report.stats),
        timing: with_timing.then(|| crate::verb::TimingView {
            stages: report.timing.stages.clone(),
            budget_ms: report.timing.budget_ms(),
            tools_ms: report.timing.tools_ms(),
        }),
        fix: report.fix.clone(),
        ticket: report.ticket.clone(),
        fail_on: Some(fail_on_name(report.fail_on).to_owned()),
        required_unresolved: report.required_unresolved(),
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
