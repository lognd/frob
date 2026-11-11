//! `frob agent heavy -- <cmd>`: run one heavy build or test command under a shared lock.
//!
//! Several agents on sibling worktrees would otherwise run cargo at once and exhaust RAM. The verb
//! takes an exclusive advisory lock under the git common dir (shared by every worktree of the
//! repository), points `CARGO_TARGET_DIR` at one shared target dir, runs the command, then deletes the
//! regenerable test executables (the biggest files in `target`). The lock is an OS file lock, so the
//! kernel releases it when this process ends however it ends: success, failure, or interrupt.

// frob:ticket 01M4P2N1TAV3MPF9G2CC274E3G

use std::fs::{File, OpenOptions};
use std::path::{Path, PathBuf};
use std::time::Duration;

use gob_cli::clap::{ArgMatches, Command as ClapCommand};
use gob_cli::{CliError, Command, Context, Outcome, Payload};
use gob_exec::{Limits, Outcome as RunOutcome, Program, Runner, Spec};
use schemars::JsonSchema;
use serde::Serialize;

use frob_tests::heavy;

use crate::agent::telemetry::{self, Basis};
use crate::pathtext;
use crate::workspace::Located;

/// File name of the shared build lock, inside the git common dir.
const LOCK_NAME: &str = "frob-heavy.lock";

/// Upper bound on one heavy command, a safety net so a hung build cannot hold the lock forever.
const MAX_RUN: Duration = Duration::from_hours(24);

/// The flags and trailing command of `agent heavy`.
#[derive(Debug, Clone, clap::Args)]
#[command(about = None, long_about = None)]
struct HeavyArgs {
    #[arg(
        long,
        value_name = "DIR",
        help = "Shared cargo target dir (default: CARGO_TARGET_DIR, else <main checkout>/target)"
    )]
    target_dir: Option<PathBuf>,
    #[arg(
        long,
        help = "Keep test executables instead of deleting them after the run"
    )]
    keep_tests: bool,
    #[arg(
        last = true,
        required = true,
        num_args = 1..,
        value_name = "CMD",
        help = "The command to run, after `--`"
    )]
    command: Vec<String>,
}

/// Output of `agent heavy`.
#[derive(Debug, Clone, Serialize, JsonSchema)]
pub struct HeavyData {
    /// The command line that ran.
    pub command: Vec<String>,
    /// The exit code of the command (-1 when it was killed by a signal).
    pub exit_code: i32,
    /// The target dir the command built into.
    pub target_dir: String,
    /// How many regenerable test executables were deleted afterwards.
    pub cleaned: usize,
}

/// Run a heavy command under the shared build lock, then clean regenerable test executables.
#[derive(Debug, Clone, gob_cli::Command)]
#[command(
    verb = "agent heavy",
    product = "frob",
    exits(ok, negative, usage, internal)
)]
pub struct AgentHeavy {
    target_dir: Option<PathBuf>,
    keep_tests: bool,
    command: Vec<String>,
}

impl Command for AgentHeavy {
    type Data = HeavyData;

    fn configure(cmd: ClapCommand) -> ClapCommand {
        gob_cli::augment::<HeavyArgs>(cmd)
    }

    fn from_matches(m: &ArgMatches) -> Result<Self, CliError> {
        let a = gob_cli::parse::<HeavyArgs>(m)?;
        Ok(Self {
            target_dir: a.target_dir,
            keep_tests: a.keep_tests,
            command: a.command,
        })
    }

    fn run(&self, ctx: &Context) -> Outcome<HeavyData> {
        let (repo, root) = Located::discover(&ctx.cwd).into_repo()?;
        let common = repo.common_dir().to_path_buf();
        let target = self
            .target_dir
            .clone()
            .or_else(|| std::env::var_os("CARGO_TARGET_DIR").map(PathBuf::from))
            .unwrap_or_else(|| shared_target(&common, &root));
        tracing::info!(lock = %pathtext::text(&common.join(LOCK_NAME)), "heavy: waiting for build lock");
        let _guard = acquire(&common).map_err(CliError::internal)?;
        tracing::info!(command = ?self.command, target = %pathtext::text(&target), "heavy: lock held; running");
        let spec = Spec {
            program: Program::Tool {
                name: self.command[0].clone(),
            },
            args: self.command[1..].to_vec(),
            cwd: Some(ctx.cwd.clone()),
            env: vec![("CARGO_TARGET_DIR".to_owned(), pathtext::text(&target))],
            timeout: MAX_RUN,
            // Not captured: the build output streams straight to the caller.
            capture: false,
        };
        let disk_before = dir_bytes(&target);
        let started = std::time::Instant::now();
        let ran = Runner::new(Limits { jobs: 1 }).run(&spec);
        let wall_ms = u64::try_from(started.elapsed().as_millis()).unwrap_or(u64::MAX);
        // Peak growth is taken before cleanup deletes the test executables.
        let disk_bytes = dir_bytes(&target).saturating_sub(disk_before);
        telemetry::record_command(
            &root,
            &heavy::command_key(&self.command),
            wall_ms,
            disk_bytes,
        );
        // Clean before the lock drops, whether or not the command succeeded.
        let cleaned = if self.keep_tests {
            0
        } else {
            let stale = stale_test_executables(&target);
            let bytes = total_bytes(&stale);
            let removed = remove_all(&stale);
            if removed > 0 {
                telemetry::record(&root, "heavy-cleanup", bytes, Basis::FreedBytes);
            }
            removed
        };
        let output =
            ran.map_err(|e| CliError::Usage(format!("cannot run `{}`: {e}", self.command[0])))?;
        let exit_code = match output.status {
            RunOutcome::Exited(c) => c,
            RunOutcome::Signaled | RunOutcome::TimedOut => -1,
        };
        tracing::info!(
            exit_code,
            cleaned,
            "heavy: command finished; releasing lock"
        );
        let data = HeavyData {
            command: self.command.clone(),
            exit_code,
            target_dir: pathtext::text(&target),
            cleaned,
        };
        if exit_code == 0 {
            Ok(Payload::new(data))
        } else {
            Err(CliError::Gate {
                message: format!("`{}` exited with {exit_code}", self.command.join(" ")),
                data: serde_json::to_value(&data).map_err(CliError::internal)?,
                warnings: Vec::new(),
            })
        }
    }
}

/// The target dir shared by every worktree: `<main checkout>/target`, else `<root>/target`.
fn shared_target(common: &Path, root: &Path) -> PathBuf {
    common
        .parent()
        .filter(|_| common.file_name().is_some_and(|n| n == ".git"))
        .unwrap_or(root)
        .join("target")
}

/// Take the exclusive build lock under `common`, blocking until it is free; dropping releases it.
pub(crate) fn acquire(common: &Path) -> std::io::Result<File> {
    let file = OpenOptions::new()
        .create(true)
        .truncate(false)
        .write(true)
        .open(common.join(LOCK_NAME))?;
    file.lock()?;
    Ok(file)
}

/// Whether `name` looks like a cargo test/bin executable in `deps`: `<crate>-<16 hex>[.exe]`.
fn is_test_executable_name(name: &str) -> bool {
    let stem = name.strip_suffix(".exe").unwrap_or(name);
    let Some((crate_part, hash)) = stem.rsplit_once('-') else {
        return false;
    };
    !crate_part.is_empty() && hash.len() == 16 && hash.bytes().all(|b| b.is_ascii_hexdigit())
}

/// Whether `meta` marks an executable regular file.
fn is_executable(path: &Path, meta: &std::fs::Metadata) -> bool {
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        let _ = path;
        meta.is_file() && meta.permissions().mode() & 0o111 != 0
    }
    #[cfg(not(unix))]
    {
        meta.is_file() && path.extension().is_some_and(|e| e == "exe")
    }
}

/// Regenerable test executables under `target`'s `{debug,release}/deps`.
pub(crate) fn stale_test_executables(target: &Path) -> Vec<PathBuf> {
    let mut roots = vec![target.to_path_buf()];
    if let Ok(rd) = std::fs::read_dir(target) {
        roots.extend(rd.flatten().map(|e| e.path()).filter(|p| p.is_dir()));
    }
    let found: Vec<PathBuf> = roots
        .iter()
        .flat_map(|root| ["debug", "release"].map(|p| root.join(p).join("deps")))
        .filter_map(|deps| std::fs::read_dir(deps).ok())
        .flat_map(Iterator::flatten)
        .filter(|e| is_test_executable_name(&pathtext::name_text(&e.file_name())))
        .filter(|e| e.metadata().is_ok_and(|m| is_executable(&e.path(), &m)))
        .map(|e| e.path())
        .collect();
    tracing::debug!(count = found.len(), target = %pathtext::text(target), "heavy: scanned test executables");
    found
}

/// Total size in bytes of the regular files under `dir` (unreadable entries count as 0).
fn dir_bytes(dir: &Path) -> u64 {
    let Ok(rd) = std::fs::read_dir(dir) else {
        return 0;
    };
    rd.flatten()
        .filter_map(|e| e.file_type().ok().map(|t| (e, t)))
        .map(|(e, t)| {
            if t.is_dir() {
                dir_bytes(&e.path())
            } else if t.is_file() {
                e.metadata().map_or(0, |m| m.len())
            } else {
                0
            }
        })
        .sum()
}

/// Total size in bytes of `paths` (unreadable ones count as 0).
fn total_bytes(paths: &[PathBuf]) -> u64 {
    paths
        .iter()
        .filter_map(|p| std::fs::metadata(p).ok())
        .map(|m| m.len())
        .sum()
}

/// Delete `paths`, logging failures; return how many were removed.
pub(crate) fn remove_all(paths: &[PathBuf]) -> usize {
    paths
        .iter()
        .filter(|p| match std::fs::remove_file(p) {
            Ok(()) => true,
            Err(e) => {
                tracing::warn!(path = %pathtext::text(p), error = %e, "heavy: cannot remove");
                false
            }
        })
        .count()
}
