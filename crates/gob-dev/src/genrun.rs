//! Running a generation: the in-process run (linked with frob by `frob-docgen`) and the delegation
//! `cargo dev gen` uses to reach it, so this crate itself never links a frob crate.

use std::path::{Path, PathBuf};
use std::time::Duration;

use clap::ValueEnum;
use gob_exec::{Limits, Outcome, Program, Runner, Spec};

use crate::out::emit;
use crate::{Kind, Mode, apply, generate, workspace_root};

/// The package that links frob and runs the generator in process.
pub const DOCGEN_PACKAGE: &str = "frob-docgen";

/// Longest a delegated generation may run (it may compile the frob crates first).
const DOCGEN_TIMEOUT: Duration = Duration::from_secs(3600);

/// Generate (or with `check`, diff) the derived files in this process.
///
/// Frob must already be registered through [`crate::products::register_frob`].
///
/// # Errors
/// A one-line message when generation or the comparison fails; in check mode, when a file is stale.
pub fn generate_files(kind: Kind, check: bool, root: Option<PathBuf>) -> Result<(), String> {
    let workspace = workspace_root().map_err(|e| format!("error: {e}"))?;
    let root = root.unwrap_or_else(|| workspace.clone());
    let mode = if check { Mode::Check } else { Mode::Write };
    tracing::info!(?kind, ?mode, root = %gob_path::Shown::of(&root), "generating");
    let files = generate(kind, &workspace.join("crates")).map_err(|e| {
        tracing::error!(error = %e, "generation failed");
        format!("error: {e}")
    })?;
    match apply(&root, &files, mode) {
        Ok(applied)
            if mode == Mode::Check && (applied.differing > 0 || applied.marker_problems > 0) =>
        {
            emit(&format!(
                "GEN001: {} of {} generated files are stale and {} marker problems; run `cargo dev gen all`",
                applied.differing, applied.total, applied.marker_problems
            ));
            Err("check failed".to_owned())
        }
        Ok(applied) => {
            emit(&format!("{} generated files up to date", applied.total));
            Ok(())
        }
        Err(e) => {
            tracing::error!(error = %e, "generation failed");
            Err(format!("error: {e}"))
        }
    }
}

/// The argument vector that makes cargo run the docgen binary for `kind`.
#[must_use]
pub fn docgen_args(kind: Kind, check: bool, root: Option<&str>) -> Vec<String> {
    let name = kind
        .to_possible_value()
        .map_or_else(|| "all".to_owned(), |v| v.get_name().to_owned());
    let mut args = vec![
        "run".to_owned(),
        "--quiet".to_owned(),
        "--package".to_owned(),
        DOCGEN_PACKAGE.to_owned(),
        "--".to_owned(),
        name,
    ];
    if check {
        args.push("--check".to_owned());
    }
    if let Some(root) = root {
        args.push("--root".to_owned());
        args.push(root.to_owned());
    }
    args
}

/// Run the generation through the frob-side binary, inheriting its output.
///
/// # Errors
/// A one-line message when the binary cannot run or exits non-zero.
pub fn delegate_to_docgen(kind: Kind, check: bool, root: Option<&Path>) -> Result<(), String> {
    let workspace = workspace_root().map_err(|e| format!("error: {e}"))?;
    let root = root
        .map(|r| {
            gob_path::exact_text(r).ok_or_else(|| "error: --root is not valid unicode".to_owned())
        })
        .transpose()?;
    let spec = Spec {
        program: Program::Cargo,
        args: docgen_args(kind, check, root),
        cwd: Some(workspace),
        env: Vec::new(),
        timeout: DOCGEN_TIMEOUT,
        capture: false,
    };
    tracing::info!(args = ?spec.args, "delegating generation to frob-docgen");
    let out = Runner::new(Limits { jobs: 1 })
        .run(&spec)
        .map_err(|e| format!("error: {DOCGEN_PACKAGE}: {e}"))?;
    match out.status {
        Outcome::Exited(0) => Ok(()),
        other => {
            tracing::error!(?other, "frob-docgen failed");
            Err(if check {
                "check failed".to_owned()
            } else {
                format!("error: {DOCGEN_PACKAGE} ended {other:?}")
            })
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    // frob:ticket 01M5H16QQT8R5N9162DMQE4F44
    #[test]
    fn docgen_args_name_the_kind_and_flags() {
        let args = docgen_args(Kind::RulesIndex, true, Some("out"));
        assert_eq!(args[3], DOCGEN_PACKAGE);
        assert_eq!(args[5], "rules-index");
        assert!(args.contains(&"--check".to_owned()));
        assert_eq!(args.last().map(String::as_str), Some("out"));
    }

    #[test]
    fn docgen_args_omit_unset_flags() {
        let args = docgen_args(Kind::All, false, None);
        assert_eq!(args.last().map(String::as_str), Some("all"));
    }
}
