//! Guard against git tracking a state or cache directory (security.md 2.2).

use std::path::Path;
use std::time::Duration;

use gob_exec::{Limits, Outcome, Program, Runner, Spec};

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
/// Directories whose tracked content makes a run refuse.
pub const STATE_DIRS: [&str; 3] = [".frob", ".grimble", ".crunk"];

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
const GIT_TIMEOUT: Duration = Duration::from_secs(30);

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
/// Why the tracked-state guard refused or could not decide.
#[derive(Debug, thiserror::Error)]
pub enum GuardError {
    /// Git tracks files under a state or cache directory.
    #[error("git tracks files under a state or cache directory: {}", files.join(", "))]
    StateTracked {
        /// Repo-relative paths of the tracked files, sorted.
        files: Vec<String>,
    },
    /// Git could not be run or gave an unusable answer.
    #[error("cannot list tracked files with git: {0}")]
    Git(String),
}

// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
/// Refuse with [`GuardError::StateTracked`] when git tracks anything under `.frob/`, `.grimble/` or `.crunk/` in `root`.
///
/// # Errors
///
/// [`GuardError::StateTracked`] names the tracked files; [`GuardError::Git`] when git cannot be run.
///
/// A `root` that is not inside a git repository passes: nothing can be tracked.
pub fn check_state_untracked(root: &Path) -> Result<(), GuardError> {
    let mut args = vec![
        "ls-files".to_owned(),
        "-z".to_owned(),
        "--full-name".to_owned(),
        "--".to_owned(),
    ];
    args.extend(STATE_DIRS.iter().map(|d| format!(":(top,literal){d}")));
    let spec = Spec {
        program: Program::Git,
        args,
        cwd: Some(root.to_owned()),
        env: Vec::new(),
        timeout: GIT_TIMEOUT,
        capture: true,
    };
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .map_err(|e| GuardError::Git(e.to_string()))?;
    match out.status {
        Outcome::Exited(0) => {}
        Outcome::Exited(128) if out.stderr.contains("not a git repository") => {
            tracing::debug!(root = %root.display(), "not a git repository; nothing tracked");
            return Ok(());
        }
        other => {
            return Err(GuardError::Git(format!(
                "git ls-files ended {other:?}: {}",
                out.stderr.trim()
            )));
        }
    }
    let mut files: Vec<String> = out
        .stdout
        .split('\0')
        .filter(|p| !p.is_empty())
        .map(str::to_owned)
        .collect();
    files.sort();
    if files.is_empty() {
        Ok(())
    } else {
        tracing::warn!(count = files.len(), "git tracks state or cache files");
        Err(GuardError::StateTracked { files })
    }
}
