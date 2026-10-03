//! `release changelog`, `release status` and `release bump` (documentation.md 6, releases.md 4).
//!
//! A thin layer over `frob-release`: ticket ULIDs resolve against the ledger, a typed
//! [`ReleaseError`] becomes an exit-3 refusal carrying its teaching message, and
//! an I/O failure is internal. `release status` gathers the milestone, the open tickets,
//! `PM034` and the changelog dry-run into [`frob_release::status::Input`] and reports; it never refuses
//! over what it finds.

use std::collections::BTreeSet;

use frob_ledger::index::ListFilter;
use frob_ledger::model::Category;
use frob_ledger::{Ledger, TicketId};
use frob_pm::PmStore;
use frob_pm::model::Milestone;
use frob_pm::rules::membership::{CLAIM_PREFIX, claimants, pm034};
use frob_release::bump::{BumpError, BumpOptions, BumpReport, LockState};
use frob_release::status::{
    ChangelogFacts, EvidenceRef, Input, MilestoneFacts, OpenTicket, Report, assess,
};
use frob_release::{Mode, Options, ReleaseError};
use gob_cli::clap::{Arg, ArgAction, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use schemars::JsonSchema;
use serde::Serialize;

use crate::config::FrobConfig;
use crate::milestone_cmd::{MilestoneView, milestones, pm_err};
use crate::ticket::{cli_err, get, open, text_flag};
use crate::workspace::{Located, config_refusal};

/// What `release changelog` did, or with `--check` and `--dry-run` would do.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct ChangelogData {
    /// The release version.
    pub version: String,
    /// `write`, `dry-run` or `check`.
    pub mode: String,
    /// The rendered section; absent when there were no fragments.
    pub section: Option<String>,
    /// Fragment file names compiled (or that would be).
    pub fragments: Vec<String>,
    /// True when CHANGELOG.md was written and the fragments removed.
    pub written: bool,
}

/// Compile changelog.d fragments into a new CHANGELOG.md section for a version.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "release changelog",
    product = "frob",
    idempotent = true,
    dry_run = true,
    exits(ok, refused, usage, internal)
)]
pub struct ReleaseChangelog {
    version: String,
    date: Option<String>,
    check: bool,
}

impl Command for ReleaseChangelog {
    type Data = ChangelogData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("version")
                .long("version")
                .required(true)
                .value_name("X")
                .help("Release version, MAJOR.MINOR.PATCH (for example 0.532.0)"),
        )
        .arg(text_flag(
            "date",
            "Section date YYYY-MM-DD (default: today)",
        ))
        .arg(
            Arg::new("check")
                .long("check")
                .action(ArgAction::SetTrue)
                .help("Validate fragments and that older sections are unedited; write nothing"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            date: get(m, "date"),
            check: m.get_flag("check"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<ChangelogData> {
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let cfg = FrobConfig::load(&root).map_err(|e| config_refusal(&e))?;
        let ledger = Ledger::open(repo, cfg.ledger());
        let mode = if self.check {
            Mode::Check
        } else if ctx.dry_run {
            Mode::DryRun
        } else {
            Mode::Write
        };
        let date = self
            .date
            .clone()
            .unwrap_or_else(|| jiff::Zoned::now().date().to_string());
        let opts = Options {
            version: self.version.clone(),
            date,
            mode,
        };
        let resolver = |ulid: &str| -> Option<String> {
            let id: TicketId = ulid.parse().ok()?;
            ledger.show(id).ok().map(|v| v.summary.handle)
        };
        let out = frob_release::run(&root, &opts, &resolver).map_err(refuse)?;
        tracing::info!(version = %self.version, ?mode, written = out.written, "release changelog");
        let already = out.section.is_none();
        Ok(Payload::new(ChangelogData {
            version: self.version.clone(),
            mode: format!("{mode:?}").to_lowercase(),
            section: out.section,
            fragments: out.fragments,
            written: out.written,
        })
        .with_already(already))
    }
}

/// Map a release error to its CLI error: refusal (exit 3) unless it is an I/O failure.
fn refuse(e: ReleaseError) -> CliError {
    let (code, remedy) = match &e {
        ReleaseError::Io { .. } => return CliError::internal(e),
        ReleaseError::Fragments(_) => (
            "E-CHANGELOG-FRAGMENT",
            "frob release changelog --check --version <X>",
        ),
        ReleaseError::InvalidVersion(_) | ReleaseError::InvalidDate(_) => {
            ("E-CHANGELOG-ARGS", "frob release changelog --help")
        }
        ReleaseError::VersionExists(_) => (
            "E-CHANGELOG-VERSION-EXISTS",
            "frob release changelog --dry-run --version <next>",
        ),
        ReleaseError::Tampered(_) | ReleaseError::Unmarked(_) => {
            ("E-CHANGELOG-EDITED", "git checkout -- CHANGELOG.md")
        }
    };
    tracing::info!(code, "release changelog refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy(remedy)
        .into()
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// What `release status` reports: a readiness report, or why there is nothing to report on.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct StatusData {
    /// `report`, or `no-milestone` when no version could be chosen.
    pub outcome: String,
    /// The explanation and the next command, when `outcome` is `no-milestone`.
    pub message: Option<String>,
    /// The readiness report; absent when `outcome` is `no-milestone`.
    pub report: Option<Report>,
}

/// Report release readiness: criteria, open tickets, PM034, fragments, what is unresolved; never fails.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "release status",
    product = "frob",
    idempotent = true,
    exits(ok, refused, internal)
)]
pub struct ReleaseStatus {
    version: Option<String>,
}

impl Command for ReleaseStatus {
    type Data = StatusData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("version")
                .value_name("VERSION")
                .help("Release version (default: the lowest open milestone)"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<StatusData> {
        let ledger = open(ctx)?;
        let all = milestones(PmStore::new(&ledger))?;
        let version = if let Some(v) = self.version.clone() {
            v
        } else if let Some(m) = lowest_open(&all) {
            m.version.clone()
        } else {
            tracing::info!("release status: no open milestone");
            return Ok(Payload::new(StatusData {
                outcome: "no-milestone".to_owned(),
                message: Some(no_milestone_message(&all)),
                report: None,
            }));
        };
        let milestone = all
            .iter()
            .find(|m| m.version == version || m.id.handle() == version);
        let version = milestone.map_or(version, |m| m.version.clone());
        let ctx_dir = Located::discover(&ctx.cwd).into_repo()?.1;
        let input = Input {
            milestone: milestone.map(|m| facts(m, &ledger)).transpose()?,
            open_tickets: open_tickets(&ledger, milestone, &version)?,
            changelog: changelog_facts(&ctx_dir, &ledger, &version),
            version,
        };
        let report = assess(&input);
        Ok(Payload::new(StatusData {
            outcome: "report".to_owned(),
            message: None,
            report: Some(report),
        }))
    }
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// The open milestone with the lowest version, comparing numeric fields so 0.9.0 sorts before 0.10.0.
fn lowest_open(all: &[Milestone]) -> Option<&Milestone> {
    all.iter()
        .filter(|m| m.state == frob_pm::State::Open)
        .min_by_key(|m| version_key(&m.version))
}

/// Sort key of a version: numeric core, with a pre-release sorting before its release.
fn version_key(v: &str) -> (Vec<u64>, bool, String) {
    let (core, pre) = v.split_once('-').map_or((v, ""), |(c, p)| (c, p));
    let nums = core
        .split('.')
        .map(|n| n.parse::<u64>().unwrap_or(0))
        .collect();
    (nums, pre.is_empty(), pre.to_owned())
}

/// The message when no version can be chosen: what exists and the command that creates a milestone.
fn no_milestone_message(all: &[Milestone]) -> String {
    if all.is_empty() {
        "no milestone exists yet; create one with `frob milestone new <VERSION> --goal <text> --criterion <text>`, or name a version to see what is labelled `release:<VERSION>`: `frob release status <VERSION>`".to_owned()
    } else {
        let list: Vec<String> = all
            .iter()
            .map(|m| format!("{} ({})", m.version, m.state))
            .collect();
        format!(
            "no open milestone ({}); name one with `frob release status <VERSION>` or create the next with `frob milestone new <VERSION> --goal <text>`",
            list.join(", ")
        )
    }
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// Milestone facts for the report: criteria with evidence, member epics, and its PM034 findings.
fn facts(m: &Milestone, ledger: &Ledger) -> Result<MilestoneFacts, CliError> {
    let view = MilestoneView::of(m, ledger);
    let tickets = claimants(ledger).map_err(pm_err)?;
    let pm034 = pm034(std::slice::from_ref(m), &tickets)
        .findings
        .into_iter()
        .map(|f| f.message)
        .collect();
    Ok(MilestoneFacts {
        handle: view.handle,
        goal: view.goal,
        state: view.state,
        epics: view
            .epics
            .iter()
            .map(|e| {
                format!(
                    "{} {}",
                    e.handle.clone().unwrap_or_else(|| e.id.clone()),
                    e.title.clone().unwrap_or_default()
                )
            })
            .collect(),
        criteria: view
            .criteria
            .into_iter()
            .map(|c| frob_release::status::CriterionStatus {
                position: c.position,
                text: c.text,
                state: c.state,
                evidence: c
                    .bound_by
                    .into_iter()
                    .map(|b| EvidenceRef {
                        provider: b.provider,
                        reference: b.reference,
                    })
                    .collect(),
            })
            .collect(),
        pm034,
    })
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// Not-done tickets below the member epics (the epics themselves excluded) or labelled `release:VERSION`.
fn open_tickets(
    ledger: &Ledger,
    milestone: Option<&Milestone>,
    version: &str,
) -> Result<Vec<OpenTicket>, CliError> {
    let mut seen: BTreeSet<TicketId> = BTreeSet::new();
    let mut found = Vec::new();
    let mut keep = |s: frob_ledger::index::Summary| {
        if s.category != Category::Done && seen.insert(s.id) {
            found.push(OpenTicket {
                handle: s.handle,
                title: s.title,
                category: s.category.to_string(),
            });
        }
    };
    let mut queue: Vec<TicketId> = milestone.map(|m| m.epics.clone()).unwrap_or_default();
    let mut visited: BTreeSet<TicketId> = queue.iter().copied().collect();
    while let Some(parent) = queue.pop() {
        let children = ledger
            .list(&ListFilter {
                parent: Some(parent),
                ..ListFilter::default()
            })
            .map_err(cli_err)?;
        for c in children {
            if visited.insert(c.id) {
                queue.push(c.id);
            }
            keep(c);
        }
    }
    let labelled = ledger
        .list(&ListFilter {
            label: Some(format!("{CLAIM_PREFIX}{version}")),
            ..ListFilter::default()
        })
        .map_err(cli_err)?;
    labelled.into_iter().for_each(keep);
    tracing::debug!(version, open = found.len(), "open tickets gathered");
    Ok(found)
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// The changelog dry-run for `version`, reduced to what the report shows; reuses [`frob_release::run`].
fn changelog_facts(root: &std::path::Path, ledger: &Ledger, version: &str) -> ChangelogFacts {
    let opts = Options {
        version: version.to_owned(),
        date: jiff::Zoned::now().date().to_string(),
        mode: Mode::DryRun,
    };
    let resolver = |ulid: &str| -> Option<String> {
        let id: TicketId = ulid.parse().ok()?;
        ledger.show(id).ok().map(|v| v.summary.handle)
    };
    match frob_release::run(root, &opts, &resolver) {
        Ok(out) => ChangelogFacts::Valid {
            fragments: out.fragments,
            section: out.section,
        },
        Err(ReleaseError::Fragments(errs)) => ChangelogFacts::InvalidFragments(
            errs.iter()
                .map(|e| (e.file().to_owned(), e.to_string()))
                .collect(),
        ),
        Err(e) => ChangelogFacts::Refused(e.to_string()),
    }
}

// frob:ticket 01M4069X2KPQ6RNV26SWSY4VA5
/// One file a bump changed (or would change) with its unified diff.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BumpFile {
    /// Path relative to the repository root.
    pub path: String,
    /// Unified diff of the edit.
    pub diff: String,
}

// frob:ticket 01M4069X2KPQ6RNV26SWSY4VA5
/// What `release bump` did, or with `--dry-run` would do.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct BumpData {
    /// The lockstep version set.
    pub version: String,
    /// The workspace version before, when it declared one.
    pub previous: Option<String>,
    /// True when nothing needed to change.
    pub already: bool,
    /// True when nothing was written because of `--dry-run`.
    pub dry_run: bool,
    /// Files changed (or that would be), excluding Cargo.lock.
    pub files: Vec<BumpFile>,
    /// `refreshed`, `unchanged`, `would-refresh`, `not-needed` or `absent`.
    pub lock: String,
    /// REL002 messages after the write; absent for a dry run, empty when clean.
    pub rel002: Option<Vec<String>>,
}

impl From<BumpReport> for BumpData {
    fn from(r: BumpReport) -> Self {
        Self {
            version: r.version,
            previous: r.previous,
            already: r.already,
            dry_run: r.dry_run,
            files: r
                .files
                .into_iter()
                .map(|f| BumpFile {
                    path: f.path,
                    diff: f.diff,
                })
                .collect(),
            lock: match r.lock {
                LockState::Refreshed => "refreshed",
                LockState::Unchanged => "unchanged",
                LockState::WouldRefresh => "would-refresh",
                LockState::NotNeeded => "not-needed",
                LockState::Absent => "absent",
            }
            .to_owned(),
            rel002: r.rel002,
        }
    }
}

// frob:ticket 01M4069X2KPQ6RNV26SWSY4VA5
/// Set one lockstep version on every crate, intra-workspace pin and the wheel; idempotent.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "release bump",
    product = "frob",
    idempotent = true,
    dry_run = true,
    exits(ok, refused, internal)
)]
pub struct ReleaseBump {
    version: String,
    allow_downgrade: bool,
}

impl Command for ReleaseBump {
    type Data = BumpData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("version")
                .value_name("VERSION")
                .required(true)
                .help("The lockstep version, semver (for example 0.532.0)"),
        )
        .arg(
            Arg::new("allow-downgrade")
                .long("allow-downgrade")
                .action(ArgAction::SetTrue)
                .help("Permit a version lower than the current workspace version"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            allow_downgrade: m.get_flag("allow-downgrade"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<BumpData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let opts = BumpOptions {
            version: self.version.clone(),
            dry_run: ctx.dry_run,
            allow_downgrade: self.allow_downgrade,
        };
        let report = frob_release::bump::run(&root, &opts).map_err(refuse_bump)?;
        tracing::info!(version = %self.version, already = report.already, dry_run = ctx.dry_run, "release bump");
        let already = report.already;
        Ok(Payload::new(BumpData::from(report)).with_already(already))
    }
}

// frob:ticket 01M4069X2KPQ6RNV26SWSY4VA5
/// Map a bump error to its CLI error: a refusal (exit 3) unless it is an I/O failure.
fn refuse_bump(e: BumpError) -> CliError {
    let (code, remedy) = match &e {
        BumpError::Io { .. } => return CliError::internal(e),
        BumpError::InvalidVersion(_) => ("E-BUMP-VERSION", "frob release bump --help"),
        BumpError::Downgrade { .. } => (
            "E-BUMP-DOWNGRADE",
            "frob release bump <VERSION> --allow-downgrade",
        ),
        BumpError::NotWorkspace(_) => ("E-BUMP-NO-WORKSPACE", "cd <repository root>"),
        BumpError::Unresolved(_) | BumpError::Shape { .. } => {
            ("E-BUMP-MANIFEST", "fix the named manifest, then rerun")
        }
        BumpError::Cargo { .. } => (
            "E-BUMP-LOCK",
            "cargo fetch, then frob release bump <VERSION>",
        ),
    };
    tracing::info!(code, "release bump refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy(remedy)
        .into()
}

/// Register the `release` verbs on the root.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<ReleaseChangelog>()
        .register::<ReleaseStatus>()
        .register::<ReleaseBump>()
}
