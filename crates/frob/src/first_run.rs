//! First-run teaching: a verb that needs `frob.toml` in a repository without one says what to run.
// frob:ticket 01M40FXV09GYGBH9YZZANDZXZ4
//!
//! The text is built once by [`teaching_message`] so broader first-run teaching can reuse it.

use std::path::Path;

use gob_cli::{CliError, Context, Refusal, RefusalClass};

use crate::workspace::Located;

/// Stable refusal code for "no frob.toml here".
pub const CODE_NO_CONFIG: &str = "E-NO-CONFIG";

/// Verbs that work without a `frob.toml` (they create it, read nothing from it, or are read-only).
const NO_CONFIG_VERBS: &[&str] = &[
    "doctor",
    "init",
    "schema",
    "config show",
    "config sync",
    "merge-driver",
];

/// The two-sentence intro, the one command, and what `frob init` writes (diagnostics.md section 5).
pub fn teaching_message() -> String {
    [
        "frob is the enforcement layer for this repository: a git-tracked ticket queue, an obligation graph and gates that keep code, tests and docs in step.",
        "This repository has no frob.toml, so run `frob init` to set it up; it will write:",
        "  - frob.toml with every enforcement knob materialized at its default",
        "  - a .gitignore entry for .frob/",
        "  - .gitattributes and the frob merge driver for the ticket ledger",
        "For a read-only look first, run `frob doctor`.",
    ]
    .join("\n")
}

/// The refusal for a verb that needs config, given whether `cwd` is inside a git work tree.
pub fn no_config_refusal(in_repo: bool) -> Refusal {
    if in_repo {
        Refusal::new(
            CODE_NO_CONFIG,
            RefusalClass::GuardNeedsAction,
            teaching_message(),
        )
        .with_remedy("frob init")
    } else {
        Refusal::new(
            CODE_NO_CONFIG,
            RefusalClass::GuardNeedsAction,
            "frob is the enforcement layer for a git repository (tickets, obligation graph, gates), and this directory is not inside one.\nRun frob inside a git work tree, or run `git init` here first and then `frob init`.\nFor a read-only look, run `frob doctor`.",
        )
        .with_remedy("git init")
    }
}

/// Guard for [`gob_cli::Cli::with_guard`]: stop config-needing verbs when `frob.toml` is absent.
///
/// # Errors
///
/// `E-NO-CONFIG` (exit 3, remedy `frob init` or `git init`) when `verb` needs config and none exists.
pub fn require_config(verb: &str, ctx: &Context) -> Result<(), CliError> {
    if NO_CONFIG_VERBS.contains(&verb) {
        tracing::debug!(verb, "verb needs no frob.toml");
        return Ok(());
    }
    check_dir(verb, &ctx.cwd)
}

/// Refuse when the repository containing `cwd` has no `frob.toml` (or `cwd` is not in one).
fn check_dir(verb: &str, cwd: &Path) -> Result<(), CliError> {
    let located = Located::discover(cwd);
    let in_repo = located.require_repo().is_ok();
    if in_repo && located.root.join("frob.toml").is_file() {
        return Ok(());
    }
    tracing::info!(verb, in_repo, root = %located.root.display(), "no frob.toml; teaching instead of running");
    Err(no_config_refusal(in_repo).into())
}
