//! `ticket doctor`: ledger integrity.

use frob_evidence::record::digest_hex;
use frob_evidence::scrub::PathScrub;
use frob_ledger::TicketId;
use frob_ledger::doctor::Issue;
use frob_ledger::scrub::{ScrubReport, ScrubTools};
use frob_pm::doctor::PmIssue;
use frob_pm::{ObjectKind, PmStore};
use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome as CliOutcome, Payload};
use schemars::JsonSchema;
use serde::Serialize;

use super::{cli_err, open, terminal_lease};
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
    /// Ledger files `--fix` rewrote to remove absolute home paths (`TICK004`).
    pub scrubbed: Vec<String>,
    /// Tickets that got a `scrub` audit event.
    pub scrubbed_tickets: Vec<TicketId>,
    /// Evidence digests recomputed over scrubbed text.
    pub scrub_digests: usize,
    /// Files whose home path the scrub could not clear.
    pub scrub_unresolved: Vec<String>,
    /// The commit that made the scrub, when there was anything to scrub.
    pub scrub_commit: Option<String>,
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
    /// Tickets whose lease (held for a terminal ticket) `--fix` removed.
    pub reaped_leases: Vec<TicketId>,
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
                .help("Rewrite frontmatter that differs from its events (TICK001, E-PM-DRIFT) and scrub absolute home paths (TICK004) and local private terms (TICK005) from the ledger in one commit"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            fix: m.get_flag("fix"),
        })
    }

    fn run(&self, ctx: &Context) -> CliOutcome<DoctorData> {
        let ledger = open(ctx)?;
        let mut report = ledger.doctor(self.fix).map_err(cli_err)?;
        report.issues.extend(unmerged_done_issues(&ledger)?);
        // frob:ticket 01M42MGN8882Y65TVXH0V1WTNR
        let stale = terminal_lease::stale_leases(ctx, &ledger)?;
        let reaped_leases = if self.fix {
            terminal_lease::reap(ctx, &stale)?
        } else {
            report
                .issues
                .extend(stale.iter().map(|(ticket, holder)| Issue {
                    code: "E-DOCTOR-TERMINAL-LEASE".to_owned(),
                    ticket: *ticket,
                    message: format!(
                        "ticket {ticket} is done but {holder} still holds its lease; `frob ticket doctor --fix` removes it"
                    ),
                }));
            Vec::new()
        };
        let scrub = if self.fix {
            scrub_ledger(&ledger)?
        } else {
            ScrubReport::default()
        };
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
        let mut findings = report.findings;
        findings.extend(ledger.home_path_findings().map_err(cli_err)?);
        // frob:ticket 01M42EZ8J63P84XFKTR2GXRW72
        findings.extend(ledger.private_term_findings().map_err(cli_err)?);
        let ok = report.issues.is_empty() && findings.is_empty() && pm.is_clean();
        let data = DoctorData {
            tickets: report.tickets,
            events: report.events,
            ok,
            issues: report.issues,
            fixed: report.fixed,
            scrubbed: scrub.files,
            scrubbed_tickets: scrub.tickets,
            scrub_digests: scrub.digests,
            scrub_unresolved: scrub.unresolved,
            scrub_commit: scrub.commit,
            milestones,
            cycles,
            pm_events: pm.events,
            pm_issues: pm.issues.into_iter().map(PmIssueView::from).collect(),
            pm_fixed: pm.fixed.iter().map(ToString::to_string).collect(),
            reaped_leases,
        };
        Ok(Payload::new(data).with_findings(findings))
    }
}

// frob:ticket 01M41RHBJ03PGD6JY0J6JTAH9Q
/// Scrub absolute home paths out of the ledger with the repair scrub of this checkout (one forward commit, none when clean).
fn scrub_ledger(ledger: &frob_ledger::Ledger) -> Result<ScrubReport, CliError> {
    let root = ledger
        .repo()
        .work_dir()
        .map(std::path::Path::to_path_buf)
        .unwrap_or_default();
    let scrub = PathScrub::for_repair(ledger.repo(), &root);
    let rewrite = |t: &str| scrub.apply(t);
    let tools = ScrubTools {
        rewrite: &rewrite,
        digest: &|b: &[u8]| digest_hex(b),
    };
    let report = ledger.scrub(&tools).map_err(cli_err)?;
    tracing::info!(
        files = report.files.len(),
        tickets = report.tickets.len(),
        digests = report.digests,
        unresolved = report.unresolved.len(),
        "ticket doctor --fix scrubbed the ledger"
    );
    Ok(report)
}

// frob:ticket 01M42M1KBKRWKN4D3A1CKZS2R3
/// One `E-DOCTOR-UNMERGED` issue per done or fixed ticket whose branch still holds commits the base lacks and that carries no `land-exempt` audit event.
fn unmerged_done_issues(ledger: &frob_ledger::Ledger) -> Result<Vec<Issue>, CliError> {
    let base = frob_worktree::work::base_branch(ledger);
    let filter = frob_ledger::index::ListFilter {
        category: Some(frob_ledger::model::Category::Done),
        ..Default::default()
    };
    let mut issues = Vec::new();
    for s in ledger.list(&filter).map_err(cli_err)? {
        if !frob_evidence::done::guards_apply(s.outcome) {
            continue;
        }
        let (unmerged, more) =
            frob_evidence::done::unmerged_commits(ledger.repo(), &base, &s.handle)
                .map_err(CliError::internal)?;
        if unmerged.is_empty() {
            continue;
        }
        if frob_ledger::event::land_exemption(&ledger.events(s.id).map_err(cli_err)?).is_some() {
            tracing::debug!(handle = %s.handle, "done ticket has unmerged commits but a land-exempt record");
            continue;
        }
        tracing::warn!(handle = %s.handle, count = unmerged.len(), "done ticket with an unmerged branch");
        issues.push(Issue {
            code: "E-DOCTOR-UNMERGED".to_owned(),
            ticket: s.id,
            message: format!(
                "{} is done but {} holds commits not merged into {base}: {}{}; land them or record why with a new ticket",
                s.handle,
                frob_evidence::done::ticket_branch(&s.handle),
                unmerged.join("; "),
                if more { "; and more" } else { "" }
            ),
        });
    }
    Ok(issues)
}
