//! The `ack` verb: attest the current digests of bound flows and symbols in `grimble.lock`.
//!
//! The decision is [`grimble_bind::ack::plan_ack`] over the gob-lock planner; this module only
//! binds the repository, then commits the lock on the current branch through `gob-git` (or writes
//! it atomically when the root is not a repository). Mirrors `frob ack` without linking frob.

// frob:ticket 01M3Z714820D1SK6X44T9R1B70

use std::path::Path;

use gob_cli::clap::{Arg, ArgAction, ArgMatches};
use gob_cli::{CliError, Command, Context, Outcome, Payload, Refusal, RefusalClass};
use gob_git::{CommitOptions, RelPath, Repo};
use grimble_bind::ack::{AckError, AckRequest, plan_ack};
use grimble_bind::{BindInput, PRODUCT};
use grimble_model::ModelFiles;
use schemars::JsonSchema;
use serde::Serialize;

use crate::workspace::{config_refusal, locate_root};

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
        AckError::Resolve { .. } | AckError::Plan(_) | AckError::Rename { .. } => {
            CliError::Usage(e.to_string())
        }
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

/// Walk and bind the repository at `root` the way `grimble check` does.
fn bind_root(root: &Path) -> Result<grimble_bind::Binding, CliError> {
    let table = gob_check::CheckTable::load(root, PRODUCT).map_err(|e| config_refusal(&e))?;
    let mut exclude = vec![format!("/.{PRODUCT}/"), "/target/".to_owned()];
    exclude.extend(table.exclude.iter().cloned());
    let walked = gob_walk::walk(
        root,
        &gob_walk::WalkConfig {
            exclude,
            size_cap: table.size_cap,
            ..gob_walk::WalkConfig::default()
        },
    )
    .map_err(CliError::internal)?;
    let mut model = ModelFiles::new();
    for f in &walked.files {
        if Path::new(&f.path)
            .extension()
            .is_some_and(|e| e.eq_ignore_ascii_case("grmb"))
        {
            match std::fs::read(root.join(&f.path)) {
                Ok(bytes) => model = model.with_file(&f.path, bytes),
                Err(err) => tracing::warn!(path = %f.path, %err, "model file unreadable; skipped"),
            }
        }
    }
    let models = grimble_check::config::GrimbleTable::load(root).map_err(|e| config_refusal(&e))?;
    let model = model.with_declared_roots(models.models);
    Ok(grimble_bind::bind(&BindInput {
        root,
        entries: &walked.files,
        model: &model,
        modeled: &[],
        strict: false,
    }))
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
            let tmp = root.join(format!("{name}.tmp"));
            std::fs::write(&tmp, bytes)
                .and_then(|()| std::fs::rename(&tmp, &path))
                .map_err(CliError::internal)?;
            Ok((None, None))
        }
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
                .help("Why the current state is acknowledged"),
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
        let root = locate_root(&ctx.cwd);
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
                at: jiff::Timestamp::now().to_string(),
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
