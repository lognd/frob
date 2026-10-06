//! grimble's view of the shared workspace helpers: `gob-product` with the product name bound.

use std::path::{Path, PathBuf};

use gob_check::CheckError;
use gob_cli::CliError;
use gob_config::{ConfigError, TableDescription, all_tables};

use crate::PRODUCT;

/// The nearest ancestor of `cwd` holding `grimble.toml` or a `.git` entry, else `cwd`.
pub(crate) fn locate_root(cwd: &Path) -> PathBuf {
    gob_product::workspace::locate_root(PRODUCT, cwd)
}

/// A config failure as a refusal naming the file to fix.
pub(crate) fn config_refusal(e: &ConfigError) -> CliError {
    gob_product::workspace::config_refusal(PRODUCT, e)
}

/// Map a pipeline failure onto the exit table (cli.md section 2).
pub(crate) fn check_error(err: CheckError) -> CliError {
    gob_product::workspace::check_error(PRODUCT, err)
}

/// Every registered config table sorted by name (inventory order is link-dependent).
pub(crate) fn registered_tables() -> Vec<TableDescription> {
    let mut tables: Vec<TableDescription> = all_tables().collect();
    tables.sort_by(|a, b| a.table.cmp(&b.table));
    tables
}
