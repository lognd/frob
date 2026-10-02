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

/// Workspace root, resolved from this crate's manifest directory.
pub fn workspace_root() -> PathBuf {
    Path::new(env!("CARGO_MANIFEST_DIR")).join("../..")
}
