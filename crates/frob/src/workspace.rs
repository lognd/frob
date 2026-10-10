//! Locating the repository root and mapping config errors to refusals.

use std::path::{Path, PathBuf};

use frob_ledger::{Ledger, RefMode};
use gob_cli::{CliError, Payload, Refusal, RefusalClass};
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

    /// Take the repo (with a work tree) and its root, or the `E-NOT-A-REPO` refusal.
    pub(crate) fn into_repo(self) -> Result<(Repo, PathBuf), CliError> {
        self.require_repo()?;
        let Self { repo, root } = self;
        Ok((
            repo.unwrap_or_else(|| unreachable!("require_repo checked")),
            root,
        ))
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

// frob:ticket 01M4FG552GZ9FMB000B76AS8XH
/// The notice for a trunk-mode ledger read from a feature branch, or `None` when the checkout is the ledger's branch.
///
/// Ticket verbs there read and commit to the trunk ref, never to the checked-out tree, which is
/// what surprised the first adopters (F-504, F-562).
pub(crate) fn ledger_site_notice(ledger: &Ledger) -> Option<String> {
    if ledger.config().mode != RefMode::Trunk {
        return None;
    }
    let ledger_ref = ledger.ledger_ref().ok()?;
    let branch = ledger.repo().current_branch().ok().flatten()?;
    if ledger_ref == format!("refs/heads/{branch}") {
        return None;
    }
    Some(format!(
        "ticket ledger: reading and committing to {ledger_ref} (ref_mode = trunk) while `{branch}` is checked out; the working tree is not the ledger, so tickets and edits on `{branch}` are invisible here until they reach {ledger_ref}"
    ))
}

// frob:ticket 01M4FG552GZ9FMB000B76AS8XH
/// Queue [`ledger_site_notice`] on the running verb's envelope (nothing when the checkout is the ledger's branch).
pub(crate) fn note_ledger_site(ledger: &Ledger) {
    if let Some(notice) = ledger_site_notice(ledger) {
        tracing::info!(%notice, "ticket verb runs off the trunk ledger branch");
        Payload::note(notice);
    }
}
