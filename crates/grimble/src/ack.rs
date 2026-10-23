//! The `ack` verb: attest the current digests of bound flows and symbols in `grimble.lock`.
//!
//! The decision is [`grimble_bind::ack::plan_ack`] over the gob-lock planner; this module only
//! binds the repository, then commits the lock on the current branch through `gob-git` (or writes
//! it atomically when the root is not a repository). Mirrors `frob ack` without linking frob.

// frob:ticket 01M3Z714820D1SK6X44T9R1B70
// frob:ticket 01M4D6NMS0EQA0B6NB9KEBHDRN

use std::path::Path;

use gob_cli::clap::{ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_lock::PlanError;
use grimble_bind::PRODUCT;
use grimble_bind::ack::{AckError, AckRequest, plan_ack};
use grimble_bind::grant_ack;
use schemars::JsonSchema;
use serde::Serialize;

use crate::presence::{Presence, authorize};
use crate::workspace::{check_error, locate_root};

/// Output of `ack`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct AckData {
    /// Symrefs and flow keys whose lock entry was added, changed or re-keyed.
    pub acked: Vec<String>,
    /// `[old, new]` anchors re-keyed by `--rename`.
    pub renamed: Vec<[String; 2]>,
    /// Stale entries re-attested by a scheme migration.
    pub reattested: Vec<String>,
    /// Stale entries whose subject vanished, removed by the migration.
    pub dropped: Vec<String>,
    /// The commit that recorded the lock, when one was made.
    pub commit: Option<String>,
    /// The branch committed on.
    pub branch: Option<String>,
    /// Grants approved by `--grants` (`node: grant`).
    pub grants: Vec<String>,
    /// The lock file, repo-relative (the grant ledger under `--grants`).
    pub lock_file: String,
    /// True when nothing was written because of `--dry-run`.
    pub dry_run: bool,
}

/// Acknowledge flows and symbols: record their digests in grimble.lock and commit it on the current branch.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "ack",
    product = "grimble",
    dry_run,
    exits(ok, usage, refused, internal)
)]
pub struct Ack {
    targets: Vec<String>,
    all: bool,
    grants: bool,
    reason: Option<String>,
    renames: Vec<(String, String)>,
}

/// The refusal or usage error an [`AckError`] becomes.
fn cli_error(e: AckError) -> CliError {
    match &e {
        AckError::Resolve { .. }
        | AckError::Plan(_)
        | AckError::Rename { .. }
        | AckError::ReasonRequired => CliError::Usage(e.to_string()),
        AckError::Refused { .. } => Refusal::new(
            "E-ACK-REFUSED",
            RefusalClass::GuardNeedsAction,
            e.to_string(),
        )
        .with_remedy("bind the identity at Must (a selector or grimble:binds) in a language at F2 or above, then rerun")
        .into(),
        AckError::Lock(_) => CliError::internal(e),
    }
}

/// Walk and bind the repository at `root` through the same entry point `grimble check` uses.
fn bind_root(root: &Path) -> Result<grimble_bind::Binding, CliError> {
    grimble_check::bind_repo(root).map_err(check_error)
}

/// Commit `bytes` as the repo-relative file `name` (the lock or the grant ledger) on the current branch; `None` outside a repository (written plainly).
fn write_lock(
    root: &Path,
    name: &str,
    bytes: Vec<u8>,
    message: &str,
) -> Result<(Option<String>, Option<String>), CliError> {
    match Repo::discover(root) {
        Ok(repo) => {
            let branch = repo
                .current_branch()
                .map_err(CliError::internal)?
                .ok_or_else(|| {
                    CliError::from(
                        Refusal::new(
                            "E-ACK-DETACHED",
                            RefusalClass::GuardNeedsAction,
                            "E-ACK-DETACHED: HEAD is detached; check out a branch before acking",
                        )
                        .with_remedy("git switch <branch>"),
                    )
                })?;
            let rel = RelPath::new(name.to_owned()).map_err(CliError::internal)?;
            let done = repo
                .commit_paths(
                    &branch,
                    &[(rel, Some(bytes))],
                    message,
                    &CommitOptions::default(),
                )
                .map_err(CliError::internal)?;
            tracing::info!(%branch, commit = %done.oid, file = name, "ack committed");
            Ok((Some(done.oid.to_string()), Some(branch)))
        }
        Err(err) => {
            tracing::warn!(%err, file = name, "not a git repository; written but not committed");
            let path = root.join(name);
            gob_fs::write_atomic(&path, &bytes).map_err(CliError::internal)?;
            Ok((None, None))
        }
    }
}

/// Approve every pending grant under `root` as the git user, if `presence` and the attesters allow it.
///
/// # Errors
///
/// `E-ATTEST-NOT-HUMAN` or `E-ATTEST-NOT-ATTESTER` when nobody here may approve; a usage or
/// internal error when the repository cannot be bound or the ledger written.
pub fn ack_grants(
    root: &Path,
    presence: &Presence,
    reason: &str,
    at: &str,
    dry_run: bool,
) -> Result<AckData, CliError> {
    let attesters = grant_ack::attesters(root);
    let identity = Repo::discover(root)
        .ok()
        .and_then(|r| r.config_user())
        .map(|(_, email)| email);
    let who = authorize(presence, identity.as_deref(), &attesters)?;
    let binding = bind_root(root)?;
    let existing = grant_ack::load(root)
        .map_err(|e| CliError::Usage(e.to_string()))?
        .unwrap_or_default();
    let next = grant_ack::approve(&binding.grants, &existing, &who, reason, at);
    let grants: Vec<String> = binding
        .grants
        .pending
        .iter()
        .map(|p| format!("{}: {}", p.node, p.name))
        .collect();
    tracing::info!(%who, approved = grants.len(), dry_run, "grant ack planned");
    let mut data = AckData {
        acked: Vec::new(),
        renamed: Vec::new(),
        reattested: Vec::new(),
        dropped: Vec::new(),
        commit: None,
        branch: None,
        grants,
        lock_file: grant_ack::LEDGER_FILE.to_owned(),
        dry_run,
    };
    let changed = next != existing;
    if !dry_run && changed {
        let message = format!("ack: {} grants\n\n{reason}", data.grants.len());
        let bytes = grant_ack::render(&next).into_bytes();
        let (commit, branch) = write_lock(root, grant_ack::LEDGER_FILE, bytes, &message)?;
        data.commit = commit;
        data.branch = branch;
    }
    Ok(data)
}

impl Ack {
    /// The argument errors that need no repository: refused before the slow bind.
    fn precheck(&self) -> Result<(), AckError> {
        if self.reason.as_deref().is_none_or(|r| r.trim().is_empty()) {
            return Err(AckError::ReasonRequired);
        }
        if self.grants {
            return Ok(());
        }
        if self.targets.is_empty() && !self.all && self.renames.is_empty() {
            return Err(AckError::Plan(PlanError::NothingToAck));
        }
        Ok(())
    }
}

/// `Ack` flags.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct AckArgs {
    #[arg(
        num_args = 0..,
        value_name = "ENTITY|SYMREF|FLOW",
        help = "A flow (flow/NAME), a contract, a symref or a path; acking a flow covers both ends"
    )]
    targets: Vec<String>,
    #[arg(
        long,
        help = "Re-ack every acked entry that still exists; with --reason it migrates a stale lock"
    )]
    all: bool,
    #[arg(
        long,
        help = "Approve every new or widened `may` grant in grimble.grants.toml (a person who is an [evidence] attester only)"
    )]
    grants: bool,
    #[arg(
        long,
        value_name = "TEXT",
        help = "Why the current state is acknowledged (required)"
    )]
    reason: Option<String>,
    #[arg(
        long,
        num_args = 2,
        value_names = ["OLD", "NEW"],
        action = ArgAction::Append,
        help = "Carry the lock entry of a vanished identity to the one that holds its Body now"
    )]
    rename: Vec<String>,
}

impl Command for Ack {
    type Data = AckData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        gob_cli::augment::<AckArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<AckArgs>(m)?;
        Ok(Self {
            targets: a.targets,
            all: a.all,
            grants: a.grants,
            reason: a.reason,
            renames: a
                .rename
                .as_chunks::<2>()
                .0
                .iter()
                .map(|[a, b]| (a.clone(), b.clone()))
                .collect(),
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<AckData> {
        self.precheck().map_err(cli_error)?;
        let root = locate_root(&ctx.cwd);
        if self.grants {
            if !self.targets.is_empty() || self.all || !self.renames.is_empty() {
                return Err(CliError::Usage(
                    "--grants approves grants only; do not combine it with targets, --all or --rename"
                        .to_owned(),
                ));
            }
            let reason = self.reason.as_deref().unwrap_or_default().trim();
            let data = ack_grants(
                &root,
                &Presence::detect(),
                reason,
                &ctx.clock.now().precise(),
                ctx.dry_run,
            )?;
            let already = data.grants.is_empty();
            return Ok(Payload::new(data).with_already(already));
        }
        if self.all && self.targets.is_empty() && self.renames.is_empty() {
            let lock = gob_lock::LockFile::load(&root.join(gob_lock::file_name(PRODUCT)))
                .map_err(|e| cli_error(AckError::Lock(e)))?;
            if lock.entries.is_empty() && lock.flows.is_empty() {
                return Err(cli_error(AckError::Plan(PlanError::NothingToAck)));
            }
        }
        let binding = bind_root(&root)?;
        let actor = Repo::discover(&root)
            .ok()
            .and_then(|r| r.config_user())
            .map_or_else(|| "unknown".to_owned(), |(n, e)| format!("{n} <{e}>"));
        let planned = plan_ack(
            &binding,
            &root,
            &AckRequest {
                targets: self.targets.clone(),
                all: self.all,
                reason: self.reason.clone(),
                renames: self.renames.clone(),
                actor,
                at: ctx.clock.now().precise(),
            },
        )
        .map_err(cli_error)?;
        let plan = planned.plan;
        let mut data = AckData {
            acked: plan.acked,
            renamed: planned.renamed.into_iter().map(|(a, b)| [a, b]).collect(),
            reattested: plan.reattested.iter().map(|r| r.key.clone()).collect(),
            dropped: plan.dropped,
            commit: None,
            branch: None,
            grants: Vec::new(),
            lock_file: gob_lock::file_name(PRODUCT),
            dry_run: ctx.dry_run,
        };
        let already = data.acked.is_empty() && data.reattested.is_empty();
        if !ctx.dry_run && !already {
            let bytes = plan
                .lock
                .to_toml()
                .map_err(CliError::internal)?
                .into_bytes();
            let n = data.acked.len().max(data.reattested.len());
            let message = match &self.reason {
                Some(r) => format!("ack: {n} entries\n\n{r}"),
                None => format!("ack: {n} entries"),
            };
            let (commit, branch) =
                write_lock(&root, &gob_lock::file_name(PRODUCT), bytes, &message)?;
            data.commit = commit;
            data.branch = branch;
        }
        Ok(Payload::new(data).with_already(already))
    }
}
