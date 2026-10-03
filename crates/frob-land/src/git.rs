//! The few git operations `land` needs that `gob-git` does not offer, spawned through `gob-exec`.
//!
//! `gob-git` has no ref update, worktree removal or branch deletion, so these
//! run `git` through the repository's own runner (the spawn counter sees them).

use std::path::Path;
use std::time::Duration;

use gob_exec::{Outcome, Program, Spec};
use gob_git::Repo;

use crate::error::LandError;

/// Wall-clock limit of one git spawn.
const TIMEOUT: Duration = Duration::from_secs(120);

/// The exit code and combined output of a finished git process.
#[derive(Debug, Clone)]
pub(crate) struct GitRun {
    /// Process exit code.
    pub code: i32,
    /// Stdout followed by stderr.
    pub text: String,
}

impl GitRun {
    /// True when git exited zero.
    pub(crate) fn ok(&self) -> bool {
        self.code == 0
    }
}

/// Run `git <args>` in `cwd` through `repo`'s runner.
pub(crate) fn git(repo: &Repo, cwd: &Path, args: &[&str]) -> Result<GitRun, LandError> {
    spawn(repo, cwd, Program::Git, args)
}

/// Run `cargo <args>` in `cwd` through `repo`'s runner (frob:ticket 01M418TM2GZ24YPQE7ECTKE1J4).
pub(crate) fn cargo(repo: &Repo, cwd: &Path, args: &[&str]) -> Result<GitRun, LandError> {
    spawn(repo, cwd, Program::Cargo, args)
}

fn spawn(repo: &Repo, cwd: &Path, program: Program, args: &[&str]) -> Result<GitRun, LandError> {
    let name = format!("{program:?}");
    let spec = Spec {
        program,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: TIMEOUT,
        capture: true,
    };
    tracing::info!(program = %name, args = %args.join(" "), cwd = %cwd.display(), "land spawn");
    let out = repo
        .runner()
        .run(&spec)
        .map_err(|e| LandError::Config(format!("{name} {}: {e}", args.join(" "))))?;
    match out.status {
        Outcome::Exited(code) => Ok(GitRun {
            code,
            text: format!("{}{}", out.stdout, out.stderr).trim().to_owned(),
        }),
        other => Err(LandError::Config(format!(
            "{name} {}: {other:?}: {}",
            args.join(" "),
            out.stderr
        ))),
    }
}
