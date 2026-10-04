//! The paths frob itself owns: never a node of the design model, so never SYS001's subject.

// frob:ticket 01M41H9Y7TTWDN6DAQ5C06R6B7

/// The ledger directory when `[tickets] dir` is absent (one definition, in gob-walk).
pub use gob_walk::DEFAULT_LEDGER_DIR;

/// The changelog fragment directory (`changelog.d/<ULID>.<type>.md`).
pub const FRAGMENT_DIR: &str = "changelog.d";

/// frob's ack lock file.
pub const FROB_LOCK: &str = "frob.lock";

/// frob's per-worktree local state directory.
pub const STATE_DIR: &str = ".frob";

/// Whether frob owns `path` (repo-relative, `/` separated) given the configured `ledger_dir`.
///
/// Owned: everything under the ledger directory, `changelog.d/`, `.frob/`, and the file
/// `frob.lock`. A directory matches whole path components, so `tickets-old/x` is not owned by
/// `tickets`.
#[must_use]
pub fn is_frob_owned(path: &str, ledger_dir: &str) -> bool {
    let ledger = ledger_dir.trim_matches('/');
    let owned = path == FROB_LOCK
        || under(path, FRAGMENT_DIR)
        || under(path, STATE_DIR)
        || (!ledger.is_empty() && under(path, ledger));
    if owned {
        tracing::trace!(path, ledger_dir, "path is frob-owned; not a SYS001 subject");
    }
    owned
}

/// Whether `path` is `dir` or lies below it.
fn under(path: &str, dir: &str) -> bool {
    path.strip_prefix(dir)
        .is_some_and(|rest| rest.starts_with('/'))
}

#[cfg(test)]
mod tests {
    use super::is_frob_owned;

    // frob:tests crates/grimble-bind/src/frob_owned.rs::is_frob_owned
    #[test]
    fn the_four_frob_owned_paths_are_owned() {
        for p in [
            "tickets/ABC/ticket.md",
            "changelog.d/X.fix.md",
            "frob.lock",
            ".frob/cache.sqlite",
        ] {
            assert!(is_frob_owned(p, "tickets"), "{p}");
        }
    }

    // frob:tests crates/grimble-bind/src/frob_owned.rs::is_frob_owned
    #[test]
    fn the_ledger_dir_comes_from_the_argument_and_matches_whole_components() {
        assert!(is_frob_owned("work/items/T1/t.md", "work/items/"));
        assert!(!is_frob_owned("tickets/T1/t.md", "work/items"));
        assert!(!is_frob_owned("tickets-old/x", "tickets"));
        assert!(!is_frob_owned("src/frob.lock.rs", "tickets"));
        assert!(!is_frob_owned("tickets", "tickets"));
    }
}
