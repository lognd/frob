//! The `[worktree]` config table and the slice of `[tickets]` and `[git]` the verbs need.

use std::path::Path;

use frob_ledger::LedgerConfig;
use gob_config::{ConfigError, ConfigTable};

/// The product whose `frob.toml` carries the tables.
const PRODUCT: &str = "frob";

/// Where `frob work` creates worktrees.
#[derive(Debug, Clone, ConfigTable)]
#[config(table = "worktree", materialize)]
pub struct WorktreeConfig {
    /// Parent directory of ticket worktrees; relative paths resolve against the
    /// primary checkout and `{repo}` stands for its directory name.
    #[config(default = "../{repo}-wt".to_owned())]
    pub dir: String,
}

impl WorktreeConfig {
    /// Load `[worktree]` from `<root>/frob.toml` (a missing file means defaults).
    ///
    /// # Errors
    ///
    /// The [`ConfigError`] for an unreadable file, bad TOML, unknown key or mistyped value.
    pub fn load(root: &Path) -> Result<Self, ConfigError> {
        Ok(gob_config::load::<Self>(root, PRODUCT)?.value)
    }
}

/// The ledger settings in `<root>/frob.toml`, defaults for anything absent.
///
/// The `frob` binary owns the validated `[tickets]` and `[git]` tables and
/// depends on this crate, so this reads just the keys [`LedgerConfig`] needs and
/// ignores the rest; `frob config show` remains the place that validates them.
///
/// # Errors
///
/// A message naming the file when it cannot be read or parsed, or when `ref_mode` is unknown.
pub fn ledger_config(root: &Path) -> Result<LedgerConfig, String> {
    frob_ledger::config::load_ledger_config(root)
}
