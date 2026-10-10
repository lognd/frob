//! `release changelog`, `release status`, `release bump` and `release cut` (documentation.md 6, releases.md 4).
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
use frob_pm::event::{AdoptData, CutData, OverrideData, PmBody, PmEvent, TransitionData};
use frob_pm::model::Milestone;
use frob_pm::model::{ObjectKind, State};
use frob_pm::rules::membership::{CLAIM_PREFIX, claimants, pm034};
use frob_pm::{NewObject, PmStore};
use frob_release::adopt::AdoptError;
use frob_release::bump::{BumpError, BumpOptions, BumpReport, LockState};
use frob_release::ci::{CiFacts, CiState, CiUnknown, check_tip};
use frob_release::cut::{CutError, CutLedger, CutPlan};
use frob_release::status::{
    ChangelogFacts, EvidenceRef, ExemptTicket, Input, MilestoneFacts, OpenTicket, Report, assess,
};
use frob_release::{Mode, Options, ReleaseError};
use gob_cli::clap::{Arg, ArgAction, ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_exec::{Limits, Program, Runner};
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
        let ledger = Ledger::open(repo, cfg.ledger(), ctx.clock.clone());
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
            .unwrap_or_else(|| ctx.clock.today().to_string());
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
        // frob:ticket 01M413T4PVDKZ014X3WB5DF7DD
        ReleaseError::Config(_) => ("E-RELEASE-CONFIG", "frob config show --effective"),
    };
    tracing::info!(code, "release changelog refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy(remedy)
        .into()
}

// frob:ticket 01M41B4KPWQVBT234N2DY20758
/// One version's CHANGELOG section body, as release notes.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct NotesData {
    /// The release version.
    pub version: String,
    /// The section body: no heading, no integrity marker, blank edges trimmed.
    pub notes: String,
}

// frob:ticket 01M41B4KPWQVBT234N2DY20758
/// Print one version's CHANGELOG section body for `gh release create --notes-file` (`--text` prints it raw).
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "release notes",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ReleaseNotes {
    version: String,
}

impl Command for ReleaseNotes {
    type Data = NotesData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("version")
                .long("version")
                .required(true)
                .value_name("X")
                .help("Release version whose CHANGELOG section to print (for example 0.532.0)"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<NotesData> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let path = root.join("CHANGELOG.md");
        let refuse_notes = |why: String| -> CliError {
            tracing::info!(version = %self.version, "release notes refused");
            Refusal::new(
                "E-CHANGELOG-NO-SECTION",
                RefusalClass::GuardNeedsAction,
                why,
            )
            .with_remedy("frob release changelog --version <X>")
            .into()
        };
        let text = std::fs::read_to_string(&path)
            .map_err(|e| refuse_notes(format!("cannot read {}: {e}", path.display())))?;
        let Some(notes) = frob_release::changelog::section_body(&text, &self.version) else {
            return Err(refuse_notes(format!(
                "CHANGELOG.md has no section for {}",
                self.version
            )));
        };
        tracing::info!(version = %self.version, bytes = notes.len(), "release notes");
        // Text mode prints these rows raw, so `--text > notes.md` is exactly the section.
        let rows = notes.lines().map(str::to_owned).collect();
        Ok(Payload::new(NotesData {
            version: self.version.clone(),
            notes,
        })
        .with_rendered(rows))
    }
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
    read_only,
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
        let report = report_for(&ledger, &ctx_dir, milestone, version)?;
        Ok(Payload::new(StatusData {
            outcome: "report".to_owned(),
            message: None,
            report: Some(report),
        }))
    }
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// The readiness report of `version` (its `milestone`, when one exists); shared by `release status` and `release cut`.
fn report_for(
    ledger: &Ledger,
    root: &std::path::Path,
    milestone: Option<&Milestone>,
    version: String,
) -> Result<Report, CliError> {
    let cfg = FrobConfig::load(root).map_err(|e| config_refusal(&e))?;
    let input = Input {
        milestone: milestone.map(|m| facts(m, ledger)).transpose()?,
        open_tickets: open_tickets(ledger, milestone, &version)?,
        exempt_tickets: exempt_tickets(ledger, milestone, &version)?,
        changelog: changelog_facts(root, ledger, &version),
        ci: ci_facts(
            root,
            &frob_worktree::work::base_branch(ledger),
            cfg.release.require_ci,
        ),
        version,
    };
    Ok(assess(&input))
}

// frob:ticket 01M4069WYA9D1EGVEBC4PT3KZB
/// CI on the tip of the `base` branch (the commit a cut would release), read through `gh`; never fails, unknown is a state.
fn ci_facts(root: &std::path::Path, base: &str, require: bool) -> CiFacts {
    let repo = gob_git::Repo::discover(root);
    let sha = repo
        .as_ref()
        .ok()
        .and_then(|r| r.rev_parse(&format!("refs/heads/{base}")).ok())
        .map(|o| o.to_string());
    let state = if let (Ok(r), Some(sha)) = (&repo, &sha) {
        check_tip(
            &Runner::new(Limits::default()),
            &Program::Tool {
                name: "gh".to_owned(),
            },
            root,
            r.remote_url("origin").as_deref(),
            sha,
        )
    } else {
        tracing::warn!(base, "base branch tip did not resolve; CI not checked");
        CiState::Unknown(CiUnknown {
            reason: format!("the base branch `{base}` does not resolve to a commit"),
            remedy: format!("create or fetch `{base}` (`[tickets] ref` names it)"),
        })
    };
    CiFacts {
        sha,
        state,
        require,
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
                        label: b.label,
                    })
                    .collect(),
            })
            .collect(),
        pm034,
    })
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// Every ticket below the member epics (the epics themselves excluded) or labelled `release:VERSION`, any category.
fn release_tickets(
    ledger: &Ledger,
    milestone: Option<&Milestone>,
    version: &str,
) -> Result<Vec<frob_ledger::index::Summary>, CliError> {
    let mut seen: BTreeSet<TicketId> = BTreeSet::new();
    let mut found = Vec::new();
    let mut keep = |s: frob_ledger::index::Summary| {
        if seen.insert(s.id) {
            found.push(s);
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
    tracing::debug!(version, tickets = found.len(), "release tickets gathered");
    Ok(found)
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// Not-done tickets of the release.
fn open_tickets(
    ledger: &Ledger,
    milestone: Option<&Milestone>,
    version: &str,
) -> Result<Vec<OpenTicket>, CliError> {
    let found: Vec<OpenTicket> = release_tickets(ledger, milestone, version)?
        .into_iter()
        .filter(|s| s.category != Category::Done)
        .map(|s| OpenTicket {
            handle: s.handle,
            title: s.title,
            category: s.category.to_string(),
        })
        .collect();
    tracing::debug!(version, open = found.len(), "open tickets gathered");
    Ok(found)
}

// frob:ticket 01M412CMSRCHNXHEEENY8ZYBDW
/// Tickets of the release that carry a `changelog-exempt` event, so a reviewer sees what shipped without a note.
fn exempt_tickets(
    ledger: &Ledger,
    milestone: Option<&Milestone>,
    version: &str,
) -> Result<Vec<ExemptTicket>, CliError> {
    let mut out = Vec::new();
    for s in release_tickets(ledger, milestone, version)? {
        let events = ledger.events(s.id).map_err(cli_err)?;
        if let Some(x) = frob_ledger::event::changelog_exemption(&events) {
            out.push(ExemptTicket {
                handle: s.handle,
                title: s.title,
                actor: x.actor,
                reason: x.reason,
            });
        }
    }
    tracing::debug!(
        version,
        exempt = out.len(),
        "changelog-exempt tickets gathered"
    );
    Ok(out)
}

// frob:ticket 01M4069WSTV5ZJMRPYR2YECX6Q
/// The changelog dry-run for `version`, reduced to what the report shows; reuses [`frob_release::run`].
fn changelog_facts(root: &std::path::Path, ledger: &Ledger, version: &str) -> ChangelogFacts {
    let opts = Options {
        version: version.to_owned(),
        date: ledger.clock().today().to_string(),
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

// frob:ticket 01M4069X6S9RJWRXX3YBZ9EG10
/// One tag a cut created.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CutTag {
    /// Tag name, for example `frob-v0.532.0`.
    pub name: String,
    /// Object id of the annotated tag.
    pub object: String,
}

// frob:ticket 01M4069X6S9RJWRXX3YBZ9EG10
/// What `release cut` did.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct CutReport {
    /// The version cut.
    pub version: String,
    /// The milestone handle that was released.
    pub milestone: String,
    /// The one release commit on the base branch.
    pub commit: String,
    /// The tags at that commit; grimble is tagged as a preview binary.
    pub tags: Vec<CutTag>,
    /// True when an interrupted cut was finished instead of started.
    pub resumed: bool,
    /// True when the base branch and tags were pushed to origin.
    pub pushed: bool,
    /// Paths the release commit changed (empty when resumed).
    pub files: Vec<String>,
    /// The recorded override reason, when readiness was overridden.
    pub override_reason: Option<String>,
}

// frob:ticket 01M4069X6S9RJWRXX3YBZ9EG10
/// Cut a release: bump, compile CHANGELOG, one commit on the base branch, tags, ledger record.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "release cut",
    product = "frob",
    idempotent = false,
    exits(ok, refused, usage, internal)
)]
pub struct ReleaseCut {
    version: String,
    override_ready: bool,
    reason: Option<String>,
    push: bool,
}

impl Command for ReleaseCut {
    type Data = CutReport;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("version")
                .value_name("VERSION")
                .required(true)
                .help("The release version, semver (for example 0.532.0); its milestone must exist"),
        )
        .arg(
            Arg::new("override")
                .long("override")
                .action(ArgAction::SetTrue)
                .help("Cut although release status is not READY; needs --reason, recorded on the milestone"),
        )
        .arg(text_flag("reason", "Why readiness is overridden (with --override)"))
        .arg(
            Arg::new("push")
                .long("push")
                .action(ArgAction::SetTrue)
                .help("Push the base branch and the tags to origin (starts the release job); default is local only"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            override_ready: m.get_flag("override"),
            reason: get(m, "reason"),
            push: m.get_flag("push"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<CutReport> {
        if self.override_ready != self.reason.is_some() {
            return Err(Refusal::new(
                "E-CUT-REASON",
                RefusalClass::UsageError,
                "--override and --reason go together: an override must say why",
            )
            .with_remedy(format!(
                "frob release cut {} --override --reason <text>",
                self.version
            ))
            .into());
        }
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let ledger = open(ctx)?;
        let base = frob_worktree::work::base_branch(&ledger);
        let all = milestones(PmStore::new(&ledger))?;
        let Some(milestone) = all.into_iter().find(|m| m.version == self.version) else {
            return Err(refuse_cut(
                &CutError::NoMilestone(self.version.clone()),
                &self.version,
                &base,
            ));
        };
        let handle = milestone.id.handle();
        let plan = CutPlan {
            root: &root,
            version: self.version.clone(),
            date: ctx.clock.today().to_string(),
            base: base.clone(),
            push: self.push,
            stop_after: None,
        };
        let resolver = |ulid: &str| -> Option<String> {
            let id: TicketId = ulid.parse().ok()?;
            ledger.show(id).ok().map(|v| v.summary.handle)
        };
        let mut gate = MilestoneCut {
            ledger: &ledger,
            root: &root,
            milestone,
            override_reason: self.reason.clone(),
        };
        let out = frob_release::cut::cut(&plan, &resolver, &mut gate)
            .map_err(|e| refuse_cut(&e, &self.version, &base))?;
        Ok(Payload::new(CutReport {
            version: out.version,
            milestone: handle,
            commit: out.commit.to_string(),
            tags: out
                .tags
                .into_iter()
                .map(|t| CutTag {
                    name: t.name,
                    object: t.object,
                })
                .collect(),
            resumed: out.resumed,
            pushed: out.pushed,
            files: out.files,
            override_reason: self.reason.clone(),
        }))
    }
}

// frob:ticket 01M4069X6S9RJWRXX3YBZ9EG10
/// The milestone's event log as the cut's ledger: readiness gate, override and cut events, release transition.
struct MilestoneCut<'a> {
    ledger: &'a Ledger,
    root: &'a std::path::Path,
    milestone: Milestone,
    override_reason: Option<String>,
}

impl MilestoneCut<'_> {
    /// The milestone's events at the ledger tip.
    fn events(&self) -> Result<Vec<PmEvent>, CutError> {
        let store = PmStore::new(self.ledger);
        let tip = self
            .ledger
            .tip_hex()
            .map_err(|e| CutError::Ledger(e.to_string()))?
            .ok_or_else(|| CutError::Ledger("the ledger has no commits".to_owned()))?;
        store
            .read_events_at(&tip, ObjectKind::Milestone, self.milestone.id)
            .map_err(|e| CutError::Ledger(e.to_string()))
    }

    /// True when a `cut` event for this version exists.
    fn has_cut_event(&self) -> Result<bool, CutError> {
        Ok(self
            .events()?
            .iter()
            .any(|e| matches!(&e.body, PmBody::Cut(d) if d.version == self.milestone.version)))
    }

    /// The milestone's current state.
    fn state(&self) -> Result<State, CutError> {
        match PmStore::new(self.ledger)
            .get(ObjectKind::Milestone, self.milestone.id)
            .map_err(|e| CutError::Ledger(e.to_string()))?
            .map(|f| f.object)
        {
            Some(frob_pm::Object::Milestone(m)) => Ok(m.state),
            _ => Err(CutError::Ledger("the milestone vanished".to_owned())),
        }
    }
}

impl CutLedger for MilestoneCut<'_> {
    fn clear(&mut self) -> Result<(), CutError> {
        let report = report_for(
            self.ledger,
            self.root,
            Some(&self.milestone),
            self.milestone.version.clone(),
        )
        .map_err(|e| CutError::Ledger(e.to_string()))?;
        if report.ready {
            return Ok(());
        }
        let Some(reason) = self.override_reason.clone() else {
            let blockers: Vec<String> = report
                .blockers
                .iter()
                .map(|b| format!("{}: {}", b.subject, b.detail))
                .collect();
            return Err(CutError::NotReady(format!(
                "{}; {}",
                report.verdict,
                blockers.join("; ")
            )));
        };
        tracing::warn!(version = %self.milestone.version, %reason, "release readiness overridden");
        PmStore::new(self.ledger)
            .append(
                ObjectKind::Milestone,
                self.milestone.id,
                PmBody::Override(OverrideData {
                    version: self.milestone.version.clone(),
                    reason,
                }),
            )
            .map_err(|e| CutError::Ledger(e.to_string()))?;
        Ok(())
    }

    fn recorded(&self) -> Result<bool, CutError> {
        Ok(self.has_cut_event()? && self.state()? == State::Released)
    }

    fn record(&mut self, data: &CutData) -> Result<(), CutError> {
        let store = PmStore::new(self.ledger);
        let ledger_err = |e: frob_pm::PmError| CutError::Ledger(e.to_string());
        if !self.has_cut_event()? {
            store
                .append(
                    ObjectKind::Milestone,
                    self.milestone.id,
                    PmBody::Cut(data.clone()),
                )
                .map_err(ledger_err)?;
        }
        if self.state()? != State::Released {
            store
                .transition(
                    ObjectKind::Milestone,
                    self.milestone.id,
                    State::Released,
                    Some(format!("release cut {}", data.version)),
                )
                .map_err(ledger_err)?;
        }
        tracing::info!(version = %data.version, commit = %data.commit, "cut recorded on the milestone");
        Ok(())
    }
}

// frob:ticket 01M4069X6S9RJWRXX3YBZ9EG10
/// Map a cut error to its CLI error: a refusal (exit 3) with the remedy, else internal.
fn refuse_cut(e: &CutError, version: &str, base: &str) -> CliError {
    if !e.is_refusal() {
        tracing::error!(%e, "release cut failed");
        return CliError::internal(e.to_string());
    }
    let msg = e.to_string();
    let code = msg.split(':').next().unwrap_or("E-CUT").to_owned();
    tracing::info!(%code, "release cut refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, msg)
        .with_remedy(e.remedy(version, base))
        .into()
}

// frob:ticket 01M4235FC39ZQYF207H8ANQEZE
/// What `release adopt` recorded, or found already recorded.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AdoptReport {
    /// The version adopted.
    pub version: String,
    /// The milestone that holds the cut.
    pub milestone: String,
    /// True when no milestone existed and one was created, already released, to hold the cut.
    pub milestone_created: bool,
    /// The commit of the first tag.
    pub commit: String,
    /// The tags recorded, with the tag object of each.
    pub tags: Vec<CutTag>,
    /// The recorded reason, when one was given.
    pub reason: Option<String>,
}

// frob:ticket 01M4235FC39ZQYF207H8ANQEZE
/// Record tags made by hand as the version's release cut; git and the remote are never touched.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "release adopt",
    product = "frob",
    idempotent = true,
    exits(ok, refused, usage, internal)
)]
pub struct ReleaseAdopt {
    version: String,
    reason: Option<String>,
}

impl Command for ReleaseAdopt {
    type Data = AdoptReport;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        cmd.arg(
            Arg::new("version")
                .value_name("VERSION")
                .required(true)
                .help("The release version whose existing tags are recorded as its cut (for example 0.1.0)"),
        )
        .arg(text_flag("reason", "Why the tags are adopted instead of cut (recorded)"))
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        Ok(Self {
            version: get(m, "version").unwrap_or_default(),
            reason: get(m, "reason"),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AdoptReport> {
        let (_, root) = Located::discover(&ctx.cwd).into_repo()?;
        let ledger = open(ctx)?;
        let data = frob_release::adopt::resolve(&root, &self.version)
            .map_err(|e| refuse_adopt(&e, &self.version))?;
        let store = PmStore::new(&ledger);
        let found = milestones(store)?
            .into_iter()
            .find(|m| m.version == self.version);
        let report = |milestone: String, created: bool| AdoptReport {
            version: data.version.clone(),
            milestone,
            milestone_created: created,
            commit: data.commit.clone(),
            tags: data
                .tags
                .iter()
                .map(|t| CutTag {
                    name: t.name.clone(),
                    object: t.object.clone(),
                })
                .collect(),
            reason: self.reason.clone(),
        };
        let (milestone, created) = match found {
            Some(m) => (m, false),
            None if ctx.dry_run => {
                tracing::info!(version = %self.version, "release adopt dry run: would create a released milestone");
                return Ok(Payload::new(report("(would be created)".to_owned(), true)));
            }
            None => {
                let applied = store
                    .create(NewObject::Milestone {
                        version: self.version.clone(),
                        goal: format!("Adopted release {}", self.version),
                        target: None,
                        criteria: Vec::new(),
                    })
                    .map_err(pm_err)?;
                tracing::info!(version = %self.version, "milestone created to hold an adopted cut");
                let frob_pm::Object::Milestone(m) = applied.object else {
                    return Err(CliError::internal(
                        "a created milestone folded to another kind",
                    ));
                };
                (m, true)
            }
        };
        let handle = milestone.id.handle();
        let holder = MilestoneCut {
            ledger: &ledger,
            root: &root,
            milestone,
            override_reason: None,
        };
        let cut_err = |e: CutError| CliError::internal(e.to_string());
        if holder.recorded().map_err(cut_err)? {
            tracing::info!(version = %self.version, "release adopt: already recorded");
            return Ok(Payload::new(report(handle, created)).with_already(true));
        }
        if ctx.dry_run {
            return Ok(Payload::new(report(handle, created)));
        }
        let mut bodies = Vec::new();
        if !holder.has_cut_event().map_err(cut_err)? {
            bodies.push(PmBody::Cut(data.clone()));
            bodies.push(PmBody::Adopt(AdoptData {
                version: data.version.clone(),
                reason: self.reason.clone(),
            }));
        }
        let from = holder.state().map_err(cut_err)?;
        if from != State::Released {
            bodies.push(PmBody::Transition(TransitionData {
                from,
                to: State::Released,
                reason: Some(format!("release adopt {}", data.version)),
                ended: None,
            }));
        }
        store
            .append_many(ObjectKind::Milestone, holder.milestone.id, bodies)
            .map_err(pm_err)?;
        tracing::info!(version = %data.version, commit = %data.commit, tags = data.tags.len(), "release adopted");
        Ok(Payload::new(report(handle, created)))
    }
}

// frob:ticket 01M4235FC39ZQYF207H8ANQEZE
/// Map an adopt error to its CLI error: a refusal (exit 3) with the remedy, else internal.
fn refuse_adopt(e: &AdoptError, version: &str) -> CliError {
    if !e.is_refusal() {
        tracing::error!(%e, "release adopt failed");
        return CliError::internal(e.to_string());
    }
    let msg = e.to_string();
    let code = msg.split(':').next().unwrap_or("E-ADOPT").to_owned();
    tracing::info!(%code, "release adopt refused");
    Refusal::new(code, RefusalClass::GuardNeedsAction, msg)
        .with_remedy(e.remedy(version))
        .into()
}

/// Register the `release` verbs on the root.
pub(crate) fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<ReleaseChangelog>()
        .register::<ReleaseNotes>()
        .register::<ReleaseStatus>()
        .register::<ReleaseBump>()
        .register::<ReleaseCut>()
        .register::<ReleaseAdopt>()
}
