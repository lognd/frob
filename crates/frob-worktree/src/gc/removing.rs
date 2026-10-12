//! Leftover `<name>.removing` worktree directories: land renames a landed worktree aside
//! and deletes it on a thread that dies with the process, so the rest must be swept later.
// frob:ticket 01M4HF7GJZZ2EX5JNABSVTM10F

use std::path::{Path, PathBuf};

use gob_git::Repo;

use super::jail::Jail;
use super::scan::scan;

/// Suffix of a worktree directory renamed aside and waiting for its deletion.
pub const SUFFIX: &str = ".removing";

/// Every `*.removing` directory directly under `parent` that no registered worktree names.
pub fn leftovers(repo: &Repo, parent: &Path) -> Vec<PathBuf> {
    let Ok(entries) = std::fs::read_dir(parent) else {
        return Vec::new();
    };
    let canon = |p: &Path| gob_exec::canonical(p).unwrap_or_else(|_| p.to_path_buf());
    let registered: Vec<PathBuf> = match repo.list_worktrees() {
        Ok(infos) => infos.iter().map(|i| canon(&i.path)).collect(),
        Err(e) => {
            tracing::warn!(error = %e, "removing sweep could not list worktrees; sweeping nothing");
            return Vec::new();
        }
    };
    let mut out: Vec<PathBuf> = entries
        .flatten()
        .filter(|e| e.file_name().to_string_lossy().ends_with(SUFFIX))
        .filter(|e| e.file_type().is_ok_and(|t| t.is_dir()))
        .map(|e| e.path())
        .filter(|p| !registered.contains(&canon(p)))
        .collect();
    out.sort();
    out
}

/// Delete each of `dirs` through a jail rooted at `parent`; returns `(dir, bytes)` removed and the failures.
pub fn sweep(parent: &Path, dirs: &[PathBuf]) -> (Vec<(PathBuf, u64)>, Vec<String>) {
    let jail = Jail::new([parent.to_path_buf()]);
    let (mut done, mut failed) = (Vec::new(), Vec::new());
    for dir in dirs {
        let bytes = scan(dir).bytes;
        match jail.remove(dir) {
            Ok(_) => {
                tracing::info!(dir = %dir.display(), bytes, "removing leftover deleted");
                done.push((dir.clone(), bytes));
            }
            Err(e) => failed.push(e),
        }
    }
    (done, failed)
}
