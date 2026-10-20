//! Git freshness hooks (`distributed-tickets.md` section 5.4): `post-checkout` and `post-merge` kick a background `frob refresh`.
//!
//! The hook body lives between two marker lines so installation is idempotent and reversible: a hook file
//! frob did not write keeps its own lines, and removal strips only the marked block.

// frob:ticket 01M5CW04M17256SKGTF195YEC4

use std::path::{Path, PathBuf};

use gob_path::Shown;

/// The git hooks that carry the freshness block (there is deliberately no `pre-push`: frob's own pushes would recurse).
pub(super) const HOOKS: [&str; 2] = ["post-checkout", "post-merge"];

const BEGIN: &str =
    "# >>> frob freshness (managed by frob init; remove with frob init --remove-hooks) >>>";
const END: &str = "# <<< frob freshness <<<";

/// The managed block: skipped in CI, inside frob's own pushes and during a rebase; never fails the git operation.
fn block() -> String {
    format!(
        "{BEGIN}\n\
if [ -z \"${{CI:-}}\" ] && [ -z \"${{FROB_SYNC_INNER:-}}\" ]; then\n\
  gd=$(git rev-parse --git-dir 2>/dev/null)\n\
  if [ -n \"$gd\" ] && [ ! -d \"$gd/rebase-merge\" ] && [ ! -d \"$gd/rebase-apply\" ]; then\n\
    (command -v frob >/dev/null 2>&1 && frob refresh --background --quiet >/dev/null 2>&1) || true\n\
  fi\n\
fi\n\
{END}\n"
    )
}

/// Split `text` around an existing managed block: (before, after), or `None` when there is none.
fn split_block(text: &str) -> Option<(&str, &str)> {
    let start = text.find(BEGIN)?;
    let end_at = text[start..].find(END)? + start;
    let after = text[end_at + END.len()..]
        .strip_prefix('\n')
        .unwrap_or(&text[end_at + END.len()..]);
    Some((&text[..start], after))
}

/// The hook file text after installing the managed block into `existing` (a missing file gets a shebang).
pub(super) fn with_block(existing: Option<&str>) -> String {
    match existing {
        None => format!("#!/bin/sh\n{}", block()),
        Some(text) => {
            if let Some((before, after)) = split_block(text) {
                format!("{before}{}{after}", block())
            } else {
                let sep = if text.ends_with('\n') || text.is_empty() {
                    ""
                } else {
                    "\n"
                };
                format!("{text}{sep}{}", block())
            }
        }
    }
}

/// The hook file text with the managed block removed, or `None` when nothing but a shebang would remain.
pub(super) fn without_block(text: &str) -> Option<String> {
    let rest = match split_block(text) {
        Some((before, after)) => format!("{before}{after}"),
        None => text.to_owned(),
    };
    let meaningful = rest
        .lines()
        .any(|l| !l.trim().is_empty() && !l.starts_with("#!"));
    meaningful.then_some(rest)
}

fn io_err(path: &Path, e: &std::io::Error) -> String {
    format!("{}: {e}", Shown::of(path))
}

fn read(path: &Path) -> Result<Option<String>, String> {
    match std::fs::read_to_string(path) {
        Ok(t) => Ok(Some(t)),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(None),
        Err(e) => Err(io_err(path, &e)),
    }
}

fn write_executable(path: &Path, text: &str) -> Result<(), String> {
    if let Some(dir) = path.parent() {
        std::fs::create_dir_all(dir).map_err(|e| io_err(dir, &e))?;
    }
    std::fs::write(path, text).map_err(|e| io_err(path, &e))?;
    #[cfg(unix)]
    {
        use std::os::unix::fs::PermissionsExt;
        std::fs::set_permissions(path, std::fs::Permissions::from_mode(0o755))
            .map_err(|e| io_err(path, &e))?;
    }
    Ok(())
}

/// Install (or refresh) the block in every hook under `hooks_dir`; the paths that changed (or would, when `dry_run`).
pub(super) fn install(hooks_dir: &Path, dry_run: bool) -> Result<Vec<PathBuf>, String> {
    let mut changed = Vec::new();
    for name in HOOKS {
        let path = hooks_dir.join(name);
        let existing = read(&path)?;
        let wanted = with_block(existing.as_deref());
        if existing.as_deref() == Some(wanted.as_str()) {
            continue;
        }
        if !dry_run {
            write_executable(&path, &wanted)?;
            tracing::info!(hook = %Shown::of(&path), "freshness hook installed");
        }
        changed.push(path);
    }
    Ok(changed)
}

/// Remove the block from every hook under `hooks_dir`, deleting a file frob alone wrote; the paths that changed.
pub(super) fn remove(hooks_dir: &Path, dry_run: bool) -> Result<Vec<PathBuf>, String> {
    let mut changed = Vec::new();
    for name in HOOKS {
        let path = hooks_dir.join(name);
        let Some(existing) = read(&path)? else {
            continue;
        };
        if !existing.contains(BEGIN) {
            continue;
        }
        if !dry_run {
            match without_block(&existing) {
                Some(rest) => write_executable(&path, &rest)?,
                None => std::fs::remove_file(&path).map_err(|e| io_err(&path, &e))?,
            }
            tracing::info!(hook = %Shown::of(&path), "freshness hook removed");
        }
        changed.push(path);
    }
    Ok(changed)
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M5CW04M17256SKGTF195YEC4
    // frob:tests crates/frob/src/init/freshness_hooks.rs::install
    #[test]
    fn install_is_idempotent_and_executable() {
        let dir = tempfile::tempdir().unwrap();
        let first = install(dir.path(), false).unwrap();
        assert_eq!(first.len(), 2);
        let body = std::fs::read_to_string(dir.path().join("post-merge")).unwrap();
        assert!(body.starts_with("#!/bin/sh\n"));
        assert!(body.contains("frob refresh --background --quiet"));
        assert!(body.contains("rebase-merge"));
        assert!(install(dir.path(), false).unwrap().is_empty());
        #[cfg(unix)]
        {
            use std::os::unix::fs::PermissionsExt;
            let mode = std::fs::metadata(dir.path().join("post-merge"))
                .unwrap()
                .permissions()
                .mode();
            assert_eq!(mode & 0o111, 0o111);
        }
    }

    // frob:ticket 01M5CW04M17256SKGTF195YEC4
    // frob:tests crates/frob/src/init/freshness_hooks.rs::install
    #[test]
    fn install_preserves_a_foreign_hook_and_remove_restores_it() {
        let dir = tempfile::tempdir().unwrap();
        let path = dir.path().join("post-checkout");
        std::fs::write(&path, "#!/bin/sh\necho mine").unwrap();
        install(dir.path(), false).unwrap();
        let text = std::fs::read_to_string(&path).unwrap();
        assert!(text.starts_with("#!/bin/sh\necho mine\n"));
        assert_eq!(text.matches(BEGIN).count(), 1);
        remove(dir.path(), false).unwrap();
        assert_eq!(
            std::fs::read_to_string(&path).unwrap(),
            "#!/bin/sh\necho mine\n"
        );
        assert!(!dir.path().join("post-merge").exists());
    }

    // frob:ticket 01M5CW04M17256SKGTF195YEC4
    // frob:tests crates/frob/src/init/freshness_hooks.rs::remove
    #[test]
    fn remove_deletes_a_frob_only_hook_and_is_a_noop_twice() {
        let dir = tempfile::tempdir().unwrap();
        install(dir.path(), false).unwrap();
        assert_eq!(remove(dir.path(), false).unwrap().len(), 2);
        assert!(!dir.path().join("post-checkout").exists());
        assert!(remove(dir.path(), false).unwrap().is_empty());
    }

    // frob:ticket 01M5CW04M17256SKGTF195YEC4
    // frob:tests crates/frob/src/init/freshness_hooks.rs::install
    #[test]
    fn dry_run_writes_nothing() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(install(dir.path(), true).unwrap().len(), 2);
        assert!(!dir.path().join("post-merge").exists());
    }
}
