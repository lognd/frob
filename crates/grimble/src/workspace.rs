//! Locating the repository root and mapping failures to CLI errors.

use std::path::{Path, PathBuf};

use gob_check::CheckError;
use gob_cli::{CliError, Refusal, RefusalClass};
use gob_config::{ConfigError, TableDescription, all_tables};

/// The nearest ancestor of `cwd` holding `grimble.toml` or a `.git` entry, else `cwd`.
pub(crate) fn locate_root(cwd: &Path) -> PathBuf {
    let found = cwd
        .ancestors()
        .find(|d| d.join("grimble.toml").is_file() || d.join(".git").exists());
    let root = found.unwrap_or(cwd).to_path_buf();
    tracing::debug!(root = %root.display(), "repository root located");
    root
}

/// A config failure as a refusal naming the file to fix.
pub(crate) fn config_refusal(e: &ConfigError) -> CliError {
    Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy("fix grimble.toml as described, then rerun")
        .into()
}

/// Map a pipeline failure onto the exit table (cli.md section 2).
pub(crate) fn check_error(err: CheckError) -> CliError {
    match err {
        CheckError::UnknownFamily(_) => CliError::Usage(err.to_string()),
        CheckError::Config(e) => config_refusal(&e),
        other => CliError::internal(other),
    }
}

/// Every registered config table sorted by name (inventory order is link-dependent).
pub(crate) fn registered_tables() -> Vec<TableDescription> {
    let mut tables: Vec<TableDescription> = all_tables().collect();
    tables.sort_by(|a, b| a.table.cmp(&b.table));
    tables
}
