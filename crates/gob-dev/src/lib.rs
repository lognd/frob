//! `gob-dev`: the generator behind `cargo dev gen` and its GEN001 check mode.
//!
//! Every generated page is a pure function of an inventory registry
//! (rules, config tables, directives, commands, schemas), so adding a rule or
//! knob needs no edit here. [`generate`] builds the files; [`files::apply`]
//! writes them or, in [`Mode::Check`], diffs them against disk.

#![allow(
    clippy::format_push_string,
    reason = "page renderers build markdown with push_str(&format!(..)) for readability"
)]

pub mod files;
pub mod import_v1;
pub mod out;
pub mod render;

use std::path::{Path, PathBuf};

pub use files::{Applied, FilesError, GenFile, Mode, apply};

/// A family of generated files selectable on the command line.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, clap::ValueEnum)]
pub enum Kind {
    /// Rule pages and the rule index.
    Rules,
    /// The directive reference.
    Directives,
    /// The config reference.
    Config,
    /// Per-product CLI verb tables.
    Cli,
    /// JSON schemas.
    Schemas,
    /// Everything above.
    All,
}

/// Force the linker to keep every crate that submits inventory entries.
///
/// Registrations live in crates the generator otherwise never calls into;
/// touching one public item of each keeps their object files in the binary.
pub fn link_inventories() {
    let verbs = frob_cli::cli();
    tracing::debug!(product = frob_cli::PRODUCT, "frob cli linked");
    drop(verbs);
    let counts = (
        gob_rules::Registry::global().len(),
        gob_config::all_tables().count(),
        gob_directives::all_directives().count(),
        gob_cli::all_commands().count(),
    );
    tracing::debug!(
        ?counts,
        "inventories linked (rules, tables, directives, commands)"
    );
}

/// Build the files for `kind`, sorted by path; `crates_dir` locates mdtest corpora.
pub fn generate(kind: Kind, crates_dir: &Path) -> Vec<GenFile> {
    link_inventories();
    let mut files = Vec::new();
    let all = kind == Kind::All;
    if all || kind == Kind::Rules {
        files.extend(render::rules::generate(crates_dir));
    }
    if all || kind == Kind::Directives {
        files.extend(render::directives::generate());
    }
    if all || kind == Kind::Config {
        files.extend(render::config::generate());
    }
    if all || kind == Kind::Cli {
        files.extend(render::cli::generate());
    }
    if all || kind == Kind::Schemas {
        files.extend(render::schemas::generate());
    }
    files.sort_by(|a, b| a.path.cmp(&b.path));
    tracing::info!(?kind, files = files.len(), "generated");
    files
}

/// No enclosing directory holds a `Cargo.toml` with a `[workspace]` table.
#[derive(Debug, thiserror::Error)]
#[error("no Cargo.toml with a [workspace] table found at or above {}", start.display())]
pub struct RootError {
    /// Directory the upward search started from.
    pub start: PathBuf,
}

/// Walk up from `start` to the first directory whose `Cargo.toml` has a `[workspace]` table.
///
/// # Errors
/// Returns [`RootError`] when no ancestor of `start` is a workspace root.
pub fn find_workspace_root(start: &Path) -> Result<PathBuf, RootError> {
    for dir in start.ancestors() {
        let Ok(text) = std::fs::read_to_string(dir.join("Cargo.toml")) else {
            continue;
        };
        let is_workspace = text
            .parse::<toml::Table>()
            .is_ok_and(|t| t.contains_key("workspace"));
        if is_workspace {
            tracing::debug!(root = %dir.display(), "workspace root found");
            return Ok(dir.to_path_buf());
        }
    }
    tracing::error!(start = %start.display(), "no workspace root found");
    Err(RootError {
        start: start.to_path_buf(),
    })
}

/// Workspace root, resolved at run time from the current directory.
///
/// # Errors
/// Returns [`RootError`] when the current directory is unreadable or outside any workspace.
pub fn workspace_root() -> Result<PathBuf, RootError> {
    let cwd = std::env::current_dir().map_err(|e| {
        tracing::error!(error = %e, "current directory unreadable");
        RootError {
            start: PathBuf::from("."),
        }
    })?;
    find_workspace_root(&cwd)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn finds_workspace_root_from_nested_dir() {
        let tmp = tempfile::tempdir().unwrap();
        std::fs::write(tmp.path().join("Cargo.toml"), "[workspace]\nmembers = []\n").unwrap();
        let member = tmp.path().join("crates/x");
        std::fs::create_dir_all(member.join("src/deep")).unwrap();
        std::fs::write(member.join("Cargo.toml"), "[package]\nname = \"x\"\n").unwrap();
        let found = find_workspace_root(&member.join("src/deep")).unwrap();
        assert_eq!(found, tmp.path());
    }

    #[test]
    fn real_workspace_found_regardless_of_compile_time_path() {
        // Start from this crate's dir; the result must be the live workspace,
        // whose generated files exist, not a compile-time-baked guess.
        let start = std::env::current_dir().unwrap();
        let root = find_workspace_root(&start).unwrap();
        assert!(root.join("crates/gob-dev/Cargo.toml").is_file());
        let files = generate(Kind::Schemas, &root.join("crates"));
        let applied = apply(&root, &files, Mode::Check).unwrap();
        assert_eq!(
            applied.differing, 0,
            "generated files differ or are missing"
        );
    }
}
