//! The few git commands the pass spawns, through the repository's own runner.
// frob:ticket 01M424QEMYGC9VZZYX9BZXZK29

use std::path::Path;
use std::time::Duration;

use gob_exec::{Outcome, Program, Spec};
use gob_git::Repo;

/// Wall-clock limit of one git spawn.
const TIMEOUT: Duration = Duration::from_secs(60);

/// Run `git <args>` in `cwd`: `(exit code, stdout then stderr)`.
///
/// # Errors
///
/// The runner's error text when git cannot be spawned or is killed by the timeout.
pub fn git(repo: &Repo, cwd: &Path, args: &[&str]) -> Result<(i32, String), String> {
    let spec = Spec {
        program: Program::Git,
        args: args.iter().map(|s| (*s).to_owned()).collect(),
        cwd: Some(cwd.to_path_buf()),
        env: Vec::new(),
        timeout: TIMEOUT,
        capture: true,
    };
    tracing::debug!(args = %args.join(" "), cwd = %cwd.display(), "gc git spawn");
    let out = repo
        .runner()
        .run(&spec)
        .map_err(|e| format!("git {}: {e}", args.join(" ")))?;
    match out.status {
        Outcome::Exited(code) => Ok((code, format!("{}{}", out.stdout, out.stderr))),
        other => Err(format!("git {} did not finish: {other:?}", args.join(" "))),
    }
}
