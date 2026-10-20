//! The `[ui]` table of `frob.toml`: how much teaching text a run prints inline.

// frob:ticket 01M3ZX7ZNF2PJ2E8WJH3CSCDFK

use crate::ConfigTable;

/// Terminal presentation settings.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "ui")]
pub struct UiTable {
    /// Inline explain text: `first` (once per rule, state in `.frob/seen.toml`), `never` (help lines only) or `always`.
    #[config(default = "first".to_owned())]
    pub teach: String,
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:tests crates/gob-config/src/ui.rs::UiTable
    #[test]
    fn ui_table_teach_defaults_to_first_and_reads_file_value() {
        let dir = tempfile::tempdir().unwrap();
        let d = crate::load::<UiTable>(dir.path(), "frob").unwrap().value;
        assert_eq!(d.teach, "first");
        std::fs::write(dir.path().join("frob.toml"), "[ui]\nteach = \"never\"\n").unwrap();
        let v = crate::load::<UiTable>(dir.path(), "frob").unwrap().value;
        assert_eq!(v.teach, "never");
    }
}
