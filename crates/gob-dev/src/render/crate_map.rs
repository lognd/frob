//! `docs/reference/crates.md`: a table of every workspace crate with its path and one-line description.
//!
//! The description is the manifest's `description`; a crate without one falls back to the first
//! `//!` line of its `src/lib.rs` (or `src/main.rs`).

// frob:ticket 01M61MM4Z8F82DCCSZ87BCYC26

use std::fmt::Write as _;
use std::path::{Path, PathBuf};

use super::{cell, md_header};
use crate::files::GenFile;

/// Repository path of the generated page.
const PATH: &str = "docs/reference/crates.md";
/// The workspace member directory, relative to the workspace root.
const CRATES_DIR: &str = "crates";
/// The description shown for a crate with neither a manifest description nor a `//!` line.
const NO_DESCRIPTION: &str = "-";

/// Why the crate map could not be generated.
#[derive(Debug, thiserror::Error)]
pub enum CrateMapError {
    /// A directory or manifest could not be read.
    #[error("read {}: {source}", gob_path::Shown::with_home(path, None))]
    Io {
        /// The path.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// A manifest is not valid TOML.
    #[error("parse {}: {source}", gob_path::Shown::with_home(path, None))]
    Parse {
        /// The manifest path.
        path: PathBuf,
        /// Underlying error.
        source: toml::de::Error,
    },
}

/// One workspace crate.
struct Krate {
    /// Package name.
    name: String,
    /// Directory relative to the workspace root, with forward slashes.
    path: String,
    /// One-line description.
    description: String,
}

/// The first `//!` line of Rust source `text`, trimmed, if any.
fn first_doc_line(text: &str) -> Option<String> {
    text.lines()
        .find_map(|l| l.trim().strip_prefix("//!").map(|d| d.trim().to_owned()))
        .filter(|d| !d.is_empty())
}

/// The description of the crate in `dir` whose manifest is `manifest`.
fn describe(dir: &Path, manifest: &toml::Table) -> String {
    let declared = manifest
        .get("package")
        .and_then(|p| p.get("description"))
        .and_then(toml::Value::as_str)
        .map(|d| d.trim().to_owned())
        .filter(|d| !d.is_empty());
    declared
        .or_else(|| {
            ["src/lib.rs", "src/main.rs"].iter().find_map(|f| {
                std::fs::read_to_string(dir.join(f))
                    .ok()
                    .and_then(|t| first_doc_line(&t))
            })
        })
        .unwrap_or_else(|| NO_DESCRIPTION.to_owned())
}

/// The sorted entries of `crates_dir`.
fn crate_dirs(crates_dir: &Path) -> Result<Vec<PathBuf>, CrateMapError> {
    let io = |source| CrateMapError::Io {
        path: crates_dir.to_path_buf(),
        source,
    };
    let mut dirs: Vec<PathBuf> = std::fs::read_dir(crates_dir)
        .map_err(io)?
        .map(|e| e.map(|e| e.path()))
        .collect::<Result<_, _>>()
        .map_err(io)?;
    dirs.sort();
    Ok(dirs)
}

/// Every crate under `crates_dir`, sorted by name.
fn collect(crates_dir: &Path) -> Result<Vec<Krate>, CrateMapError> {
    let io = |path: &Path| {
        let path = path.to_path_buf();
        move |source| CrateMapError::Io { path, source }
    };
    let dirs = crate_dirs(crates_dir)?;
    let mut out = Vec::new();
    for dir in dirs {
        let manifest_path = dir.join("Cargo.toml");
        let text = match std::fs::read_to_string(&manifest_path) {
            Ok(text) => text,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => continue,
            Err(source) => return Err(io(&manifest_path)(source)),
        };
        let manifest = text
            .parse::<toml::Table>()
            .map_err(|source| CrateMapError::Parse {
                path: manifest_path.clone(),
                source,
            })?;
        let Some(name) = manifest
            .get("package")
            .and_then(|p| p.get("name"))
            .and_then(toml::Value::as_str)
        else {
            tracing::debug!(dir = ?dir, "manifest without a package name skipped");
            continue;
        };
        let dir_name = gob_path::forward_slashes(dir.strip_prefix(crates_dir).unwrap_or(&dir));
        out.push(Krate {
            name: name.to_owned(),
            path: format!("{CRATES_DIR}/{dir_name}"),
            description: describe(&dir, &manifest),
        });
    }
    out.sort_by(|a, b| a.name.cmp(&b.name));
    Ok(out)
}

/// The page text for `crates`.
fn render(crates: &[Krate]) -> String {
    let mut out = md_header("crate-map");
    out.push_str("\n# Crate map\n\n");
    out.push_str("Every workspace crate with its path and a one-line description.\n\n");
    out.push_str("| Crate | Path | Description |\n|---|---|---|\n");
    for k in crates {
        writeln!(
            out,
            "| `{}` | `{}` | {} |",
            k.name,
            k.path,
            cell(&k.description)
        )
        .ok();
    }
    out
}

/// The crate map page under the standard generated marker, read from the workspace at `root`.
///
/// # Errors
/// [`CrateMapError`] when a manifest cannot be read or parsed.
pub fn generate(root: &Path) -> Result<Vec<GenFile>, CrateMapError> {
    tracing::debug!(path = PATH, "rendering crate map");
    let crates = collect(&root.join(CRATES_DIR))?;
    tracing::info!(crates = crates.len(), "mapped crates");
    Ok(vec![GenFile {
        path: PATH.to_owned(),
        content: render(&crates),
    }])
}

#[cfg(test)]
mod tests {
    use super::*;

    /// A workspace with `a` (manifest description) and `b` (lib.rs doc fallback).
    fn fixture() -> tempfile::TempDir {
        let dir = tempfile::tempdir().expect("tempdir");
        for (name, manifest, lib) in [
            ("a", "description = \"Alpha crate.\"\n", ""),
            ("b", "", "//! Beta from lib.\n\npub fn f() {}\n"),
        ] {
            let c = dir.path().join(CRATES_DIR).join(name);
            std::fs::create_dir_all(c.join("src")).expect("mkdir");
            std::fs::write(
                c.join("Cargo.toml"),
                format!("[package]\nname = \"{name}\"\n{manifest}"),
            )
            .expect("manifest");
            std::fs::write(c.join("src/lib.rs"), lib).expect("lib");
        }
        dir
    }

    #[test]
    // frob:tests crates/gob-dev/src/render/crate_map.rs::generate
    fn lists_each_crate_with_path_and_manifest_description() {
        let dir = fixture();
        let files = generate(dir.path()).expect("generate");
        assert_eq!(files.len(), 1);
        assert_eq!(files[0].path, PATH);
        assert!(
            files[0]
                .content
                .contains("| `a` | `crates/a` | Alpha crate. |"),
            "{}",
            files[0].content
        );
        assert_eq!(crate::files::marker_problem(&files[0].content), None);
    }

    #[test]
    // frob:tests crates/gob-dev/src/render/crate_map.rs::describe
    fn falls_back_to_the_first_lib_doc_line() {
        let dir = fixture();
        let files = generate(dir.path()).expect("generate");
        assert!(
            files[0]
                .content
                .contains("| `b` | `crates/b` | Beta from lib. |"),
            "{}",
            files[0].content
        );
    }
}
