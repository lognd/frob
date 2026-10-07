//! Per-crate rule indexes (`crates/<crate>/src/rules/mod.rs`, D107): `cargo dev gen rules-index`.
//!
//! The scan and the rendering live in [`gob_rules::indexgen`] so the crate freshness test and this
//! generator can never disagree; this module finds the crates, checks that each rule's family is
//! one the crate owns (`[package.metadata.gob] families`, failure #14 of rule-authoring.md) and
//! turns the result into [`GenFile`]s so GEN001 covers them like every other generated file.

use std::path::{Path, PathBuf};

use gob_rules::indexgen::{self, IndexError};

use crate::files::GenFile;

/// Why the rule indexes could not be generated.
#[derive(Debug, thiserror::Error)]
pub enum RulesIndexError {
    /// A crate's rule files could not be indexed.
    #[error(transparent)]
    Index(#[from] IndexError),
    /// A directory could not be listed.
    #[error("read {}: {source}", path.display())]
    Io {
        /// The directory.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
    /// A rule lives in a crate that does not own its family.
    #[error("{rule}: family `{family}` is not in `[package.metadata.gob] families` of {}", manifest.display())]
    ForeignFamily {
        /// The rule id.
        rule: String,
        /// Its family prefix.
        family: String,
        /// The crate manifest naming the owned families.
        manifest: PathBuf,
    },
}

/// Directories under `root` that hold a `src/rules` directory (real crates and test fixtures).
fn rule_crates(root: &Path, out: &mut Vec<PathBuf>) -> Result<(), RulesIndexError> {
    let io = |source| RulesIndexError::Io {
        path: root.to_path_buf(),
        source,
    };
    if root.join("src").join("rules").is_dir() {
        out.push(root.to_path_buf());
    }
    for entry in std::fs::read_dir(root).map_err(io)? {
        let path = entry.map_err(io)?.path();
        let skip = path
            .file_name()
            .and_then(|n| n.to_str())
            .is_none_or(|n| n == "target" || n.starts_with('.'));
        if path.is_dir() && !skip {
            rule_crates(&path, out)?;
        }
    }
    Ok(())
}

/// The families a crate declares it owns, if its manifest says.
fn owned_families(crate_dir: &Path) -> Option<(PathBuf, Vec<String>)> {
    let manifest = crate_dir.join("Cargo.toml");
    let table: toml::Table = std::fs::read_to_string(&manifest).ok()?.parse().ok()?;
    let families = table
        .get("package")?
        .get("metadata")?
        .get("gob")?
        .get("families")?
        .as_array()?
        .iter()
        .filter_map(|v| v.as_str().map(str::to_owned))
        .collect();
    Some((manifest, families))
}

/// The family prefix of a rule id: its leading letters.
fn family_of(id: &str) -> &str {
    id.trim_end_matches(|c: char| c.is_ascii_digit())
}

/// One generated `src/rules/mod.rs` per crate under `crates_dir` that has `#[rule(..)]` rules.
///
/// # Errors
/// [`RulesIndexError`] when a rule file is malformed, a directory cannot be read, or a rule's
/// family is not owned by its crate.
pub fn generate(crates_dir: &Path) -> Result<Vec<GenFile>, RulesIndexError> {
    let workspace = crates_dir.parent().unwrap_or(crates_dir);
    let mut dirs = Vec::new();
    rule_crates(crates_dir, &mut dirs)?;
    let mut files = Vec::new();
    for dir in dirs {
        let rules = indexgen::scan(&dir)?;
        let Some(content) = indexgen::expected(&dir)? else {
            continue;
        };
        if let Some((manifest, families)) = owned_families(&dir) {
            for r in &rules {
                let family = family_of(&r.id);
                if !families.iter().any(|f| f == family) {
                    tracing::error!(rule = %r.id, family, "rule in a crate that does not own its family");
                    return Err(RulesIndexError::ForeignFamily {
                        rule: r.id.clone(),
                        family: family.to_owned(),
                        manifest,
                    });
                }
            }
        }
        let rel = dir
            .strip_prefix(workspace)
            .unwrap_or(&dir)
            .join("src")
            .join("rules")
            .join("mod.rs");
        tracing::debug!(crate_dir = %dir.display(), rules = rules.len(), "rules index generated");
        files.push(GenFile {
            path: rel.to_string_lossy().replace('\\', "/"),
            content,
        });
    }
    Ok(files)
}
