//! Locating the repository root, the no-config guard and mapping failures to CLI errors.

use std::path::{Path, PathBuf};

use gob_check::CheckError;
use gob_cli::{CliError, Context, Refusal, RefusalClass};
use gob_config::ConfigError;

/// Stable refusal code for "no crunk.toml here".
pub const CODE_NO_CONFIG: &str = "E-NO-CONFIG";

/// Verbs that work without a `crunk.toml` (read-only or built in).
const NO_CONFIG_VERBS: &[&str] = &["doctor", "schema"];

/// The nearest ancestor of `cwd` holding `crunk.toml` or a `.git` entry, else `cwd`.
pub fn locate_root(cwd: &Path) -> PathBuf {
    let found = cwd
        .ancestors()
        .find(|d| d.join("crunk.toml").is_file() || d.join(".git").exists());
    let root = found.unwrap_or(cwd).to_path_buf();
    tracing::debug!(root = %root.display(), "repository root located");
    root
}

/// Guard for [`gob_cli::Cli::with_guard`]: stop config-needing verbs when `crunk.toml` is absent.
///
/// # Errors
///
/// `E-NO-CONFIG` (exit 3, remedy: create `crunk.toml`) when `verb` needs config and none exists.
pub fn require_config(verb: &str, ctx: &Context) -> Result<(), CliError> {
    if NO_CONFIG_VERBS.contains(&verb) {
        tracing::debug!(verb, "verb needs no crunk.toml");
        return Ok(());
    }
    let root = locate_root(&ctx.cwd);
    if crunk_check::has_config(&root) {
        return Ok(());
    }
    tracing::info!(verb, root = %root.display(), "no crunk.toml; refusing");
    Err(Refusal::new(
        CODE_NO_CONFIG,
        RefusalClass::GuardNeedsAction,
        format!("no crunk.toml found at or above {}", ctx.cwd.display()),
    )
    .with_remedy(
        "create crunk.toml at the project root (an empty file is a valid config), then rerun",
    )
    .into())
}

/// A config failure as a refusal naming the file to fix.
pub(crate) fn config_refusal(e: &ConfigError) -> CliError {
    Refusal::new("E-CONFIG", RefusalClass::GuardNeedsAction, e.to_string())
        .with_remedy("fix crunk.toml as described, then rerun")
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
