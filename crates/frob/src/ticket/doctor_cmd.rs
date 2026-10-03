//! `ticket doctor`: ledger integrity.

use frob_ledger::TicketId;
use frob_ledger::doctor::Issue;
use frob_pm::doctor::PmIssue;
use frob_pm::{ObjectKind, PmStore};
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::{cli_err, open};
use crate::milestone_cmd::pm_err;

/// Output of `ticket doctor`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct DoctorData {
    /// Tickets examined.
    pub tickets: usize,
    /// Events examined.
    pub events: usize,
    /// True when no finding or issue remains.
    pub ok: bool,
    /// Problems that are not TICK rules.
    pub issues: Vec<Issue>,
    /// Tickets whose frontmatter `--fix` rewrote.
    pub fixed: Vec<TicketId>,
    /// Milestones examined.
    pub milestones: usize,
    /// Cycles examined.
    pub cycles: usize,
    /// Milestone and cycle events examined.
    pub pm_events: usize,
    /// Milestone and cycle problems (`E-PM-*` codes).
    pub pm_issues: Vec<PmIssueView>,
    /// Milestone or cycle ULIDs whose frontmatter `--fix` rewrote.
    pub pm_fixed: Vec<String>,
}

/// A milestone or cycle problem as reported by `ticket doctor`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct PmIssueView {
    /// Stable `E-PM-*` code.
    pub code: String,
    /// `milestone` or `cycle`.
    pub kind: String,
    /// The object directory name.
    pub subject: String,
    /// What is wrong.
    pub message: String,
}

impl From<PmIssue> for PmIssueView {
    fn from(i: PmIssue) -> Self {
        Self {
            code: i.code.to_owned(),
            kind: i.kind.to_string(),
            subject: i.subject,
            message: i.message,
        }
    }
}

/// Re-fold every ticket, milestone and cycle and report frontmatter drift, dangling links and event-order problems.
#[derive(Debug, Clone, Copy, gob_cli::Command)]
#[command(
    verb = "ticket doctor",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct TicketDoctor {
    fix: bool,
}

impl Command for TicketDoctor {
    type Data = DoctorData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("fix")
                .long("fix")
                .action(ArgAction::SetTrue)
                .help("Rewrite frontmatter that differs from its events (TICK001, E-PM-DRIFT)"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            fix: m.get_flag("fix"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<DoctorData> {
        let ledger = open(ctx)?;
        let report = ledger.doctor(self.fix).map_err(cli_err)?;
        let pm = PmStore::new(&ledger).doctor(self.fix).map_err(pm_err)?;
        let count_of = |kind: ObjectKind| {
            let tip = ledger.tip_hex().map_err(cli_err)?;
            Ok::<usize, CliError>(match tip {
                Some(t) => PmStore::new(&ledger)
                    .ids_at(&t, kind)
                    .map_err(pm_err)?
                    .len(),
                None => 0,
            })
        };
        let milestones = count_of(ObjectKind::Milestone)?;
        let cycles = count_of(ObjectKind::Cycle)?;
        tracing::info!(
            milestones,
            cycles,
            pm_issues = pm.issues.len(),
            pm_fixed = pm.fixed.len(),
            "ticket doctor ran the pm checks"
        );
        let ok = report.is_clean() && pm.is_clean();
        let data = DoctorData {
            tickets: report.tickets,
            events: report.events,
            ok,
            issues: report.issues,
            fixed: report.fixed,
            milestones,
            cycles,
            pm_events: pm.events,
            pm_issues: pm.issues.into_iter().map(PmIssueView::from).collect(),
            pm_fixed: pm.fixed.iter().map(ToString::to_string).collect(),
        };
        Ok(Payload::new(data).with_findings(report.findings))
    }
}
