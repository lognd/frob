//! The `[tickets] dir` of `frob.toml`, read leniently for crates that only classify paths.

use std::path::Path;

/// The ledger directory when `frob.toml` has no `[tickets] dir`.
pub const DEFAULT_LEDGER_DIR: &str = "tickets";

/// The `[tickets] dir` of `<root>/frob.toml`; [`DEFAULT_LEDGER_DIR`] when absent or unreadable.
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
            "no [tickets] dir; default ledger dir"
        );
        DEFAULT_LEDGER_DIR.to_owned()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-config/src/ledger_dir.rs::ledger_dir
    #[test]
    fn the_ledger_dir_is_configurable_and_defaults() {
        let dir = tempfile::tempdir().unwrap();
        assert_eq!(ledger_dir(dir.path()), "tickets");
        std::fs::write(dir.path().join("frob.toml"), "[tickets]\ndir = \"pm\"\n").unwrap();
        assert_eq!(ledger_dir(dir.path()), "pm");
    }
}
