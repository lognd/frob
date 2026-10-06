//! Workspace discovery, the no-config guard and the failure-to-refusal mapping.

use std::path::{Path, PathBuf};

use gob_check::CheckError;
use gob_cli::{CliError, Context, Refusal, RefusalClass};
use gob_config::ConfigError;

use crate::Product;

/// Stable refusal code for "no `<product>.toml` here".
pub const CODE_NO_CONFIG: &str = "E-NO-CONFIG";

/// Verbs that work without a config file (read-only or built in).
const NO_CONFIG_VERBS: &[&str] = &["doctor", "schema"];

/// The nearest ancestor of `cwd` holding `<product>.toml` or a `.git` entry, else `cwd`.
pub fn locate_root(product: &str, cwd: &Path) -> PathBuf {
    let config = format!("{product}.toml");
    let found = cwd
        .ancestors()
        .find(|d| d.join(&config).is_file() || d.join(".git").exists());
    let root = found.unwrap_or(cwd).to_path_buf();
    tracing::debug!(root = %root.display(), "repository root located");
    root
}

/// Guard for [`gob_cli::Cli::with_guard`]: stop config-needing verbs when `<NAME>.toml` is absent.
///
/// # Errors
///
/// `E-NO-CONFIG` (exit 3, remedy: create the file) when `verb` needs config and none exists.
pub fn require_config<P: Product>(verb: &str, ctx: &Context) -> Result<(), CliError> {
    if NO_CONFIG_VERBS.contains(&verb) {
        tracing::debug!(verb, "verb needs no config file");
        return Ok(());
    }
    let root = locate_root(P::NAME, &ctx.cwd);
    if P::has_config(&root) {
        return Ok(());
    }
    tracing::info!(verb, root = %root.display(), "no config file; refusing");
    Err(Refusal::new(
        CODE_NO_CONFIG,
        RefusalClass::GuardNeedsAction,
        format!(
            "no {}.toml found at or above {}",
            P::NAME,
            ctx.cwd.display()
        ),
    )
    .with_remedy(format!(
        "create {}.toml at the project root (an empty file is a valid config), then rerun",
        P::NAME
    ))
    .into())
}

/// A config failure as a refusal naming the file to fix.
pub fn config_refusal(product: &str, e: &ConfigError) -> CliError {
    Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy(format!("fix {product}.toml as described, then rerun"))
        .into()
}

/// Map a pipeline failure onto the exit table (cli.md section 2).
pub fn check_error(product: &str, err: CheckError) -> CliError {
    match err {
        CheckError::UnknownFamily(_) => CliError::Usage(err.to_string()),
        CheckError::Config(e) => config_refusal(product, &e),
        other => CliError::internal(other),
    }
}
