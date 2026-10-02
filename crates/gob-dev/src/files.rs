//! Generated files, write mode and check mode (one `Mode` for every generator).

use std::path::{Path, PathBuf};

use similar::TextDiff;

use crate::out::emit;

/// Whether a run writes generated files or only compares them.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Mode {
    /// Write every file, creating directories as needed.
    Write,
    /// Write nothing; report differences (GEN001).
    Check,
}

/// One generated file: a repo-relative path and its full content.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GenFile {
    /// Path relative to the output root, with `/` separators.
    pub path: String,
    /// Complete file content.
    pub content: String,
}

/// Failure to read or write a generated file.
#[derive(Debug, thiserror::Error)]
pub enum FilesError {
    /// An I/O operation on a generated path failed.
    #[error("{op} {path}: {source}")]
    Io {
        /// What was attempted.
        op: &'static str,
        /// The path involved.
        path: PathBuf,
        /// Underlying error.
        source: std::io::Error,
    },
}

/// Result of applying a set of files under a root.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Applied {
    /// Files whose content changed (write mode) or differs (check mode).
    pub differing: usize,
    /// Files examined.
    pub total: usize,
}

/// Write or check `files` under `root`; in check mode print a unified diff per differing file.
///
/// # Errors
/// Returns [`FilesError`] when a file cannot be read (other than missing) or written.
pub fn apply(root: &Path, files: &[GenFile], mode: Mode) -> Result<Applied, FilesError> {
    let mut applied = Applied {
        differing: 0,
        total: files.len(),
    };
    for file in files {
        let target = root.join(&file.path);
        let existing = match std::fs::read_to_string(&target) {
            Ok(text) => Some(text),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => None,
            Err(source) => {
                return Err(FilesError::Io {
                    op: "read",
                    path: target,
                    source,
                });
            }
        };
        let same = existing.as_deref() == Some(file.content.as_str());
        match mode {
            Mode::Check => {
                if !same {
                    tracing::warn!(path = %file.path, missing = existing.is_none(), "generated file differs");
                    applied.differing += 1;
                    emit(&unified_diff(
                        &file.path,
                        existing.as_deref(),
                        &file.content,
                    ));
                }
            }
            Mode::Write => {
                if same {
                    tracing::debug!(path = %file.path, "unchanged");
                } else {
                    if let Some(parent) = target.parent() {
                        std::fs::create_dir_all(parent).map_err(|source| FilesError::Io {
                            op: "create dir",
                            path: parent.to_path_buf(),
                            source,
                        })?;
                    }
                    std::fs::write(&target, &file.content).map_err(|source| FilesError::Io {
                        op: "write",
                        path: target.clone(),
                        source,
                    })?;
                    tracing::info!(path = %file.path, "wrote");
                    applied.differing += 1;
                    emit(&format!("wrote {}", file.path));
                }
            }
        }
    }
    Ok(applied)
}

/// Unified diff of `old` (None means the file is missing) against `new` for `path`.
pub fn unified_diff(path: &str, old: Option<&str>, new: &str) -> String {
    let old_header = if old.is_some() {
        format!("a/{path}")
    } else {
        "/dev/null".to_owned()
    };
    let new_header = format!("b/{path}");
    TextDiff::from_lines(old.unwrap_or(""), new)
        .unified_diff()
        .context_radius(3)
        .header(&old_header, &new_header)
        .to_string()
}
