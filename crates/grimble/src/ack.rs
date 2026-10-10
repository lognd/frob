//! The `ack` verb: attest the current digests of bound flows and symbols in `grimble.lock`.
//!
//! The decision is [`grimble_bind::ack::plan_ack`] over the gob-lock planner; this module only
//! binds the repository, then commits the lock on the current branch through `gob-git` (or writes
//! it atomically when the root is not a repository). Mirrors `frob ack` without linking frob.

// frob:ticket 01M3Z714820D1SK6X44T9R1B70
// frob:ticket 01M4D6NMS0EQA0B6NB9KEBHDRN

use std::path::Path;

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_git::{CommitOptions, RelPath, Repo};
use gob_lock::PlanError;
use grimble_bind::PRODUCT;
use grimble_bind::ack::{AckError, AckRequest, plan_ack};
use schemars::JsonSchema;
use serde::Serialize;

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
    /// The lock file, repo-relative.
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

/// Commit `bytes` as the lock on the current branch; `None` outside a repository (written plainly).
fn write_lock(
    root: &Path,
    bytes: Vec<u8>,
    message: &str,
) -> Result<(Option<String>, Option<String>), CliError> {
    let name = gob_lock::file_name(PRODUCT);
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
            let rel = RelPath::new(name).map_err(CliError::internal)?;
            let done = repo
                .commit_paths(
                    &branch,
                    &[(rel, Some(bytes))],
                    message,
                    &CommitOptions::default(),
                )
                .map_err(CliError::internal)?;
            tracing::info!(%branch, commit = %done.oid, "grimble.lock committed");
            Ok((Some(done.oid.to_string()), Some(branch)))
        }
        Err(err) => {
            tracing::warn!(%err, "not a git repository; grimble.lock written but not committed");
            let path = root.join(&name);
            gob_fs::write_atomic(&path, &bytes).map_err(CliError::internal)?;
            Ok((None, None))
        }
    }
}

impl Ack {
    /// The argument errors that need no repository: refused before the slow bind.
    fn precheck(&self) -> Result<(), AckError> {
        if self.reason.as_deref().is_none_or(|r| r.trim().is_empty()) {
            return Err(AckError::ReasonRequired);
        }
        if self.targets.is_empty() && !self.all && self.renames.is_empty() {
            return Err(AckError::Plan(PlanError::NothingToAck));
        }
        Ok(())
    }
}

impl Command for Ack {
    type Data = AckData;

    fn configure(cmd: gob_cli::clap::Command) -> gob_cli::clap::Command {
        cmd.arg(
            Arg::new("targets")
                .num_args(0..)
                .value_name("ENTITY|SYMREF|FLOW")
                .help("A flow (flow/NAME), a contract, a symref or a path; acking a flow covers both ends"),
        )
        .arg(
            Arg::new("all")
                .long("all")
                .action(ArgAction::SetTrue)
                .help("Re-ack every acked entry that still exists; with --reason it migrates a stale lock"),
        )
        .arg(
            Arg::new("reason")
                .long("reason")
                .value_name("TEXT")
                .help("Why the current state is acknowledged (required)"),
        )
        .arg(
            Arg::new("rename")
                .long("rename")
                .num_args(2)
                .value_names(["OLD", "NEW"])
                .action(ArgAction::Append)
                .help("Carry the lock entry of a vanished identity to the one that holds its Body now"),
        )
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let flat: Vec<String> = m
            .get_many::<String>("rename")
            .map(|v| v.cloned().collect())
            .unwrap_or_default();
        Ok(Self {
            targets: m
                .get_many::<String>("targets")
                .map(|v| v.cloned().collect())
                .unwrap_or_default(),
            all: m.get_flag("all"),
            reason: m.get_one::<String>("reason").cloned(),
            renames: flat
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
            let (commit, branch) = write_lock(&root, bytes, &message)?;
            data.commit = commit;
            data.branch = branch;
        }
        Ok(Payload::new(data).with_already(already))
    }
}
