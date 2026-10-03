//! The `test` verb: `frob test --base <ref> [--all] [--dry-run]`.

use frob_evidence::provider::build_record;
use frob_evidence::record::Provider;
use frob_evidence::{EvidenceError, Workspace, events};
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use crate::error::TestsError;
use crate::lease::lease_ticket;
use crate::run::{RunOptions, join_args, run};
use crate::select::{TestTarget, select_tests};
use crate::touched::{TouchedSet, build_repo_graph, touched_set};

/// The evidence event a run appended to the leased ticket.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct EvidenceAdded {
    /// The ticket's handle with `~`.
    pub ticket: String,
    /// The new event's id.
    pub event: String,
    /// The ledger commit holding it.
    pub commit: String,
}

/// The failing test names for the refusal message, or a note that none were captured.
fn failed_names(failed: &[String]) -> String {
    if failed.is_empty() {
        "no failing test name captured".to_owned()
    } else {
        failed.join(", ")
    }
}

/// Output of `frob test`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct TestData {
    /// The base ref the touched set was computed against (absent with `--all`).
    pub base: Option<String>,
    /// True when nothing was run.
    pub dry_run: bool,
    /// The touched set the selection came from.
    pub touched: TouchedSet,
    /// The selected tests.
    pub selected: Vec<TestTarget>,
    /// One `package test_path` line per selected test.
    pub plan: Vec<String>,
    /// Whether nextest ran.
    pub ran: bool,
    /// The verdict, when it ran.
    pub passed: Option<bool>,
    /// Names of the tests that executed.
    pub executed: Vec<String>,
    /// Names of the tests that failed, timed out or crashed.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub failed: Vec<String>,
    /// The evidence event, when the run happened in a lease-holding worktree.
    pub evidence: Option<EvidenceAdded>,
}

/// Run only the tests that reach the files changed against a base, and record the evidence.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "test",
    product = "frob",
    dry_run,
    exits(ok, negative, refused, usage, internal)
)]
pub struct TestVerb {
    base: Option<String>,
    all: bool,
}

/// The payload of `data` carrying `warnings`.
fn with_warnings(data: TestData, warnings: Vec<String>) -> Payload<TestData> {
    let mut payload = Payload::new(data);
    payload.warnings = warnings;
    payload
}

impl Command for TestVerb {
    type Data = TestData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("base")
                .long("base")
                .value_name("REF")
                .help("Ref to diff the work tree against (required unless --all)"),
        )
        .arg(
            Arg::new("all")
                .long("all")
                .action(ArgAction::SetTrue)
                .help("Run every test of the workspace instead of the touched set"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let base = m.get_one::<String>("base").cloned();
        let all = m.get_flag("all");
        if base.is_none() && !all {
            return Err(CliError::Usage(
                "test needs --base <ref> (or --all)".to_owned(),
            ));
        }
        Ok(Self { base, all })
    }

    fn run(&self, ctx: &Context) -> Outcome<TestData> {
        let ws = Workspace::open(&ctx.cwd).map_err(EvidenceError::into_cli)?;
        let repo = ws.ledger.repo();
        let (touched, selected) = match (&self.base, self.all) {
            (Some(base), false) => {
                let graph = build_repo_graph(&ws.root).map_err(TestsError::into_cli)?;
                let touched = touched_set(repo, &graph, base).map_err(TestsError::into_cli)?;
                let selected = select_tests(&ws.root, &graph, &touched);
                (touched, selected)
            }
            _ => (TouchedSet::default(), Vec::new()),
        };
        let plan: Vec<String> = selected
            .iter()
            .map(|t| format!("{} {}", t.package, t.test_path))
            .collect();
        let mut data = TestData {
            base: self.base.clone(),
            dry_run: ctx.dry_run,
            touched,
            selected,
            plan,
            ran: false,
            passed: None,
            executed: Vec::new(),
            failed: Vec::new(),
            evidence: None,
        };
        let mut warnings: Vec<String> = data
            .touched
            .selection_findings()
            .into_iter()
            .map(|f| format!("unresolved {}: {}", f.rule, f.message))
            .collect();
        if ctx.dry_run {
            tracing::info!(selected = data.selected.len(), "dry run: nothing executed");
            return Ok(with_warnings(data, warnings));
        }
        if !self.all && data.selected.is_empty() {
            tracing::info!("no tests reach the touched set; nothing to run");
            warnings.push("no tests reach the touched set; nothing was run".to_owned());
            return Ok(with_warnings(data, warnings));
        }
        let opts = RunOptions {
            root: ws.root.clone(),
            timeout: ws.timeout(),
            profile: ws.evidence.nextest_profile.clone(),
            all: self.all,
        };
        let report = run(&ws.runner(), &data.selected, &opts).map_err(TestsError::into_cli)?;
        data.ran = true;
        data.passed = Some(report.capture.passed);
        data.executed.clone_from(&report.capture.tests);
        data.failed.clone_from(&report.capture.failed_tests);
        match lease_ticket(repo.common_dir(), &ws.root) {
            Some(reference) => match ws.ledger.resolve(&reference) {
                Ok(id) => {
                    let reference_line = join_args(&report.args);
                    let record = build_record(
                        &ws.store,
                        Provider::Nextest,
                        &reference_line,
                        &report.capture,
                        &[],
                    )
                    .map_err(EvidenceError::into_cli)?;
                    let appended = events::append(&ws.ledger, id, &record)
                        .map_err(EvidenceError::into_cli)?;
                    let handle = ws.ledger.show(id).map_or(reference, |v| v.summary.handle);
                    data.evidence = Some(EvidenceAdded {
                        ticket: handle,
                        event: appended.event.to_string(),
                        commit: appended.commit.to_string(),
                    });
                }
                Err(e) => {
                    tracing::warn!(error = %e, reference, "lease names an unknown ticket; no evidence recorded");
                    warnings.push(format!("lease ticket `{reference}` not found; no evidence recorded"));
                }
            },
            None => warnings.push(
                "not in a lease-holding worktree; no evidence recorded (use `frob ticket evidence add`)"
                    .to_owned(),
            ),
        }
        if report.capture.passed {
            let mut payload = Payload::new(data);
            payload.warnings = warnings;
            Ok(payload)
        } else {
            Err(CliError::Negative(format!(
                "tests failed ({} executed, exit {:?}): {}{}",
                data.executed.len(),
                report.capture.exit_code,
                failed_names(&data.failed),
                data.evidence.as_ref().map_or(String::new(), |e| format!(
                    "; evidence {} recorded on {}",
                    e.event, e.ticket
                ))
            )))
        }
    }
}
