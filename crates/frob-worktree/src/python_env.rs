//! A uv project's virtual environment in a fresh ticket worktree.
//!
//! `.venv` is gitignored, so a new worktree has none. A shared environment that is an editable
//! install of the primary checkout would make the worktree's tests import the primary's code, so
//! the worktree gets its own: `uv sync` with `UV_PROJECT_ENVIRONMENT` pinned to the worktree's
//! `.venv`, which installs the project editable from the worktree. It is best effort: no uv,
//! no network or a failing sync is logged and `frob work` still succeeds (a uv-run check stage
//! then syncs or reports Unresolved with the remedy).

use std::path::Path;
use std::time::Duration;

use gob_exec::{Outcome, Program, Runner, Spec};
use gob_path::Shown;

/// Environment variable naming the directory uv uses as the project environment.
const PROJECT_ENV_VAR: &str = "UV_PROJECT_ENVIRONMENT";

/// How long one `uv sync` may run.
const SYNC_TIMEOUT: Duration = Duration::from_secs(600);

/// What [`ensure_worktree_venv`] did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum VenvOutcome {
    /// The checkout is not a uv project, or the primary checkout has no environment to replace.
    NotApplicable,
    /// The checkout already has a `.venv` (a real one, or a link someone made on purpose); left alone.
    Present,
    /// `uv sync` created the environment; `offline` says it was satisfied from the cache alone.
    Created {
        /// True when the offline attempt sufficed.
        offline: bool,
    },
    /// The sync could not run or failed; the checkout has no usable environment yet.
    Failed,
}

/// Give a fresh `checkout` of a uv project its own `.venv` when the `primary` checkout has one.
///
/// Tries `uv sync --offline` first (the cache usually has every wheel), then online. Never
/// touches the primary environment: `UV_PROJECT_ENVIRONMENT` is pinned to the checkout.
// frob:ticket 01M5MMEYZXZW5MNXSTMZ9F7SRN
#[must_use]
pub fn ensure_worktree_venv(
    runner: &Runner,
    uv: &Program,
    primary: &Path,
    checkout: &Path,
) -> VenvOutcome {
    if !checkout.join("pyproject.toml").is_file()
        || !primary.join(".venv").join("pyvenv.cfg").is_file()
    {
        tracing::debug!(checkout = %Shown::of(checkout), "no uv environment to replicate");
        return VenvOutcome::NotApplicable;
    }
    let venv = checkout.join(".venv");
    if std::fs::symlink_metadata(&venv).is_ok() {
        tracing::info!(venv = %Shown::of(&venv), "worktree already has a .venv; left alone");
        return VenvOutcome::Present;
    }
    let Some(pin) = gob_path::exact_text(&venv) else {
        tracing::warn!(venv = %Shown::of(&venv), "worktree path is not UTF-8; cannot pin the uv environment");
        return VenvOutcome::Failed;
    };
    let mut base = vec!["sync".to_owned()];
    if checkout.join("uv.lock").is_file() {
        base.push("--frozen".to_owned());
    }
    for offline in [true, false] {
        let mut args = base.clone();
        if offline {
            args.push("--offline".to_owned());
        }
        let spec = Spec {
            program: uv.clone(),
            args,
            cwd: Some(checkout.to_path_buf()),
            env: vec![(PROJECT_ENV_VAR.to_owned(), pin.to_owned())],
            timeout: SYNC_TIMEOUT,
            capture: true,
        };
        match runner.run(&spec) {
            Ok(out) if out.status == Outcome::Exited(0) => {
                tracing::info!(venv = %Shown::of(&venv), offline, "worktree environment synced");
                return VenvOutcome::Created { offline };
            }
            Ok(out) => {
                tracing::warn!(offline, status = ?out.status, stderr = %out.stderr.trim(), "uv sync failed in the new worktree");
            }
            Err(err) => {
                tracing::warn!(%err, "uv could not run; the worktree has no .venv until a uv stage syncs it");
                return VenvOutcome::Failed;
            }
        }
    }
    VenvOutcome::Failed
}
