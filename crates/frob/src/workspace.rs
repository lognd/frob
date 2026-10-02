//! Locating the repository root and mapping config errors to refusals.

use std::path::{Path, PathBuf};

use gob_cli::{CliError, Refusal, RefusalClass};
use gob_config::{ConfigError, TableDescription, all_tables};
use gob_git::Repo;

/// Where a verb runs: the repository if there is one, else just a directory.
pub(crate) struct Located {
    /// The discovered repository, when `cwd` is inside one.
    pub repo: Option<Repo>,
    /// Work tree root when a repo with a work tree was found, else `cwd`.
    pub root: PathBuf,
}

impl Located {
    /// Discover the repository containing `cwd`.
    pub(crate) fn discover(cwd: &Path) -> Self {
        match Repo::discover(cwd) {
            Ok(repo) => {
                let root = repo
                    .work_dir()
                    .map_or_else(|| cwd.to_path_buf(), Path::to_path_buf);
                tracing::debug!(root = %root.display(), "repository discovered");
                Self {
                    repo: Some(repo),
                    root,
                }
            }
            Err(e) => {
                tracing::debug!(error = %e, "no repository");
                Self {
                    repo: None,
                    root: cwd.to_path_buf(),
                }
            }
        }
    }

    /// The repo and its work tree, or the `E-NOT-A-REPO` refusal.
    pub(crate) fn require_repo(&self) -> Result<&Repo, CliError> {
        match &self.repo {
            Some(r) if r.work_dir().is_some() => Ok(r),
            _ => Err(Refusal::new(
                "E-NOT-A-REPO",
                RefusalClass::GuardNeedsAction,
                format!("{} is not inside a git work tree", self.root.display()),
            )
            .with_remedy("git init")
            .into()),
        }
    }
}

/// A config failure as a refusal naming the file to fix.
pub(crate) fn config_refusal(e: &ConfigError) -> CliError {
    Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy("fix frob.toml as described, then rerun")
        .into()
}

/// Borrow all registered tables as the slice shape gob-config wants.
pub(crate) fn table_refs(tables: &[TableDescription]) -> Vec<&TableDescription> {
    tables.iter().collect()
}

/// Every registered config table sorted by name (inventory order is link-dependent).
pub(crate) fn registered_tables() -> Vec<TableDescription> {
    let mut tables: Vec<TableDescription> = all_tables().collect();
    tables.sort_by(|a, b| a.table.cmp(&b.table));
    tables
}
