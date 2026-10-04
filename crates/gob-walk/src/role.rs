//! File roles: the one structural classification of what a walked file is (D91).
//!
//! The ticket ledger tree (the configured `[tickets] dir`) is data written through the ledger
//! write path. Text in it, such as a quoted `frob:waive`, is never a live directive. Directive and
//! comment scanning asks [`Roles::role`] and skips [`FileRole::Ledger`] files; ledger-specific
//! rules (`TICK*`, `PM*`, privacy) read the ledger directly and are unaffected.

use std::path::Path;

/// The ledger directory when `frob.toml` has no `[tickets] dir`.
pub const DEFAULT_LEDGER_DIR: &str = "tickets";

/// What a file is to the checker, decided once from its path and the configured ledger directory.
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum FileRole {
    /// Ordinary repository content: code, docs, config.
    Source,
    /// A file under the ticket ledger tree: data, never a source of live directives.
    Ledger,
}

impl FileRole {
    /// True when comments in a file of this role are scanned for directives.
    #[must_use]
    pub fn scans_directives(self) -> bool {
        matches!(self, Self::Source)
    }
}

/// Classifies repository-relative paths by [`FileRole`] for one configured ledger directory.
#[derive(Clone, Debug)]
pub struct Roles {
    ledger_dir: String,
}

impl Roles {
    /// Roles for the ledger directory `ledger_dir` (relative to the repository root).
    #[must_use]
    pub fn new(ledger_dir: &str) -> Self {
        Self {
            ledger_dir: ledger_dir.trim_matches('/').to_owned(),
        }
    }

    /// Roles for the repository at `root`, reading `[tickets] dir` from `frob.toml` leniently.
    #[must_use]
    pub fn for_root(root: &Path) -> Self {
        Self::new(&ledger_dir(root))
    }

    /// The role of `path` (repository-relative, `/` separated).
    ///
    /// A directory matches whole path components, so `tickets-old/x` is not ledger content.
    #[must_use]
    pub fn role(&self, path: &str) -> FileRole {
        let ledger = !self.ledger_dir.is_empty()
            && path
                .strip_prefix(self.ledger_dir.as_str())
                .is_some_and(|rest| rest.starts_with('/'));
        if ledger {
            tracing::trace!(path, "ledger file: not scanned for directives");
            FileRole::Ledger
        } else {
            FileRole::Source
        }
    }
}

/// The ledger directory of `<root>/frob.toml` (`[tickets] dir`); the default when absent or unreadable.
#[must_use]
pub fn ledger_dir(root: &Path) -> String {
    let dir = std::fs::read_to_string(root.join("frob.toml"))
        .ok()
        .and_then(|text| text.parse::<toml::Table>().ok())
        .and_then(|t| t.get("tickets")?.get("dir")?.as_str().map(str::to_owned));
    if let Some(d) = dir {
        tracing::debug!(dir = %d, "ledger dir read from frob.toml [tickets]");
        d
    } else {
        tracing::debug!(
            dir = DEFAULT_LEDGER_DIR,
            "no [tickets] dir in frob.toml; default ledger dir"
        );
        DEFAULT_LEDGER_DIR.to_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn ledger_files_match_whole_components_and_are_not_scanned() {
        let roles = Roles::new("tickets/");
        assert_eq!(roles.role("tickets/X/ticket.md"), FileRole::Ledger);
        assert!(!roles.role("tickets/X/ticket.md").scans_directives());
        assert_eq!(roles.role("tickets-old/x.md"), FileRole::Source);
        assert_eq!(roles.role("src/tickets/x.rs"), FileRole::Source);
        assert_eq!(roles.role("tickets"), FileRole::Source);
        assert!(roles.role("src/lib.rs").scans_directives());
    }

    #[test]
    fn the_ledger_dir_is_configurable_and_defaults() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(ledger_dir(dir.path()), "tickets");
        std::fs::write(dir.path().join("frob.toml"), "[tickets]\ndir = \"pm\"\n").unwrap();
        let roles = Roles::for_root(dir.path());
        assert_eq!(roles.role("pm/A/ticket.md"), FileRole::Ledger);
        assert_eq!(roles.role("tickets/A/ticket.md"), FileRole::Source);
    }
}
