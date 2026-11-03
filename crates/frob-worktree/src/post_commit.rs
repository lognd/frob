//! A post-commit hook that warms the check memo while the developer keeps working.
//!
//! Tool stages are most of a `frob check --ticket` run and their results are memoised by input
//! hash (`<git common dir>/frob/check-results`). The hook started here runs the check detached
//! after every commit on a `ticket/*` branch of a linked worktree, so by the time the developer
//! runs `check` or `land` the memo is already warm. The hook is shared by all worktrees (it lives in
//! `<common>/hooks`) and decides at run time whether it applies, so the main checkout and every
//! non-ticket branch are untouched. A hook somebody else wrote is never replaced.

use std::path::{Path, PathBuf};

use gob_path::Shown;

/// Marker line that identifies a hook this module wrote (and may therefore rewrite).
pub const HOOK_MARKER: &str = "# frob-managed: speculative check";

/// Environment variable that turns the background check off when set to a non-empty value.
pub const OPT_OUT_ENV: &str = "FROB_NO_SPECULATIVE_CHECK";

/// What [`install_post_commit_hook`] did.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HookOutcome {
    /// The hook was written or refreshed.
    Installed,
    /// The hook is already current.
    Current,
    /// A hook that frob did not write is in place; left alone.
    Foreign,
    /// The hook could not be written.
    Failed,
}

/// The hook script: detached `frob check --ticket ~<handle>` for a linked worktree on `ticket/<handle>`.
#[must_use]
pub fn hook_script() -> String {
    format!(
        "#!/bin/sh\n{HOOK_MARKER}\n\
[ -z \"${OPT_OUT_ENV}\" ] || exit 0\n\
branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null) || exit 0\n\
case \"$branch\" in ticket/?*) ;; *) exit 0 ;; esac\n\
[ -f \"$(git rev-parse --git-dir)/commondir\" ] || exit 0\n\
command -v frob >/dev/null 2>&1 || exit 0\n\
handle=\"~${{branch#ticket/}}\"\n\
( FROB_SPECULATIVE_CHECK=1 nohup frob check --ticket \"$handle\" >/dev/null 2>&1 </dev/null & ) >/dev/null 2>&1\n\
exit 0\n"
    )
}

/// Install the shared post-commit hook under `common` (the git common dir); best effort, never fatal.
// frob:ticket 01M4NX4T2TPAM4RXM43173HKCF
#[must_use]
pub fn install_post_commit_hook(common: &Path) -> HookOutcome {
    let path: PathBuf = common.join("hooks").join("post-commit");
    let script = hook_script();
    match std::fs::read_to_string(&path) {
        Ok(existing) if existing == script => {
            tracing::debug!(hook = %Shown::of(&path), "post-commit hook already current");
            return HookOutcome::Current;
        }
        Ok(existing) if !existing.contains(HOOK_MARKER) => {
            tracing::info!(hook = %Shown::of(&path), "a foreign post-commit hook exists; speculative check not installed");
            return HookOutcome::Foreign;
        }
        Ok(_) => {
            tracing::info!(hook = %Shown::of(&path), "refreshing the managed post-commit hook");
        }
        Err(error) => {
            tracing::debug!(hook = %Shown::of(&path), %error, "no readable post-commit hook; installing");
        }
    }
    if let Err(e) = write_executable(&path, &script) {
        tracing::warn!(hook = %Shown::of(&path), error = %e, "post-commit hook not installed; no speculative check");
        return HookOutcome::Failed;
    }
    tracing::info!(hook = %Shown::of(&path), "installed the speculative-check post-commit hook");
    HookOutcome::Installed
}

fn write_executable(path: &Path, text: &str) -> std::io::Result<()> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir)?;
    }
    std::fs::write(path, text)?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o755))?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests install_post_commit_hook
    #[test]
    fn installs_then_is_current_and_refuses_a_foreign_hook() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(install_post_commit_hook(dir.path()), HookOutcome::Installed);
        assert_eq!(install_post_commit_hook(dir.path()), HookOutcome::Current);
        let hook = dir.path().join("hooks/post-commit");
        let text = std::fs::read_to_string(&hook).unwrap();
        assert!(text.contains("frob check --ticket"));
        std::fs::write(&hook, "#!/bin/sh\necho mine\n").unwrap();
        assert_eq!(install_post_commit_hook(dir.path()), HookOutcome::Foreign);
        assert!(std::fs::read_to_string(&hook).unwrap().contains("mine"));
    }

    // frob:tests install_post_commit_hook
    #[test]
    fn a_stale_managed_hook_is_refreshed() {
        let dir = tempfile::tempdir().unwrap();
        let hook = dir.path().join("hooks/post-commit");
        std::fs::create_dir_all(hook.parent().unwrap()).unwrap();
        std::fs::write(&hook, format!("#!/bin/sh\n{HOOK_MARKER}\nold\n")).unwrap();
        assert_eq!(install_post_commit_hook(dir.path()), HookOutcome::Installed);
        assert_eq!(std::fs::read_to_string(&hook).unwrap(), hook_script());
    }

    // frob:tests hook_script
    #[test]
    fn the_script_only_fires_for_ticket_branches_of_linked_worktrees() {
        let s = hook_script();
        assert!(s.contains("FROB_SPECULATIVE_CHECK=1 nohup frob check"));
        assert!(s.contains("ticket/?*"));
        assert!(s.contains("commondir"));
        assert!(s.contains(OPT_OUT_ENV));
        assert!(s.is_ascii());
    }
}
