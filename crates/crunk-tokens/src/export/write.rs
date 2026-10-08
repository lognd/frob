//! Writing the generated files atomically, and the shared export error.

// frob:ticket 01M43ARZH9F9MCPJCKXM635E0X

use std::path::{Path, PathBuf};

use crunk_spec::DesignSpec;
use serde::Serialize;

use super::Target;
use super::drift::{Rendered, collisions, render_managed_with};
use crate::model::{ThemeCollision, TokenError, TokenSet};

/// Why an export could not be written or checked.
#[derive(Debug, thiserror::Error)]
pub enum ExportError {
    /// The spec produced a colliding token name.
    #[error(transparent)]
    Token(#[from] TokenError),
    /// A generated file exists but could not be read.
    #[error("cannot read {}: {source}", path.display())]
    Read {
        /// The file.
        path: PathBuf,
        /// The OS error.
        #[source]
        source: std::io::Error,
    },
    /// A generated file could not be written.
    #[error("cannot write {}: {source}", path.display())]
    Write {
        /// The file.
        path: PathBuf,
        /// The OS error.
        #[source]
        source: std::io::Error,
    },
}

/// What [`write_all`] wrote.
#[derive(Debug, Clone, PartialEq, Serialize)]
pub struct WriteReport {
    /// The files written, in [`Target::ALL`] order: (target name, path).
    pub written: Vec<WrittenFile>,
    /// Tailwind default theme keys the un-namespaced export redefines.
    pub collisions: Vec<ThemeCollision>,
    /// Non-fatal notes (a possibly orphaned copy of a generated file).
    pub warnings: Vec<String>,
}

/// One file [`write_all`] wrote.
#[derive(Debug, Clone, PartialEq, Eq, Serialize)]
pub struct WrittenFile {
    /// Which export this is.
    pub target: Target,
    /// Where it was written.
    pub path: PathBuf,
}

/// Render and atomically write every configured generated file, creating parent directories.
///
/// # Errors
///
/// [`ExportError::Token`] for a colliding token name, [`ExportError::Write`] when a file cannot
/// be written (files written before it stay written; each write is atomic).
pub fn write_all(spec: &DesignSpec) -> Result<WriteReport, ExportError> {
    let tokens = TokenSet::from_spec(spec)?;
    let rendered = render_managed_with(spec, &tokens);
    let mut written = Vec::with_capacity(rendered.len());
    for file in &rendered {
        write_one(file)?;
        written.push(WrittenFile {
            target: file.target,
            path: file.path.clone(),
        });
    }
    let report = WriteReport {
        written,
        collisions: collisions(spec, &tokens),
        warnings: orphan_warnings(spec, &rendered),
    };
    tracing::info!(files = report.written.len(), "tokens written");
    Ok(report)
}

fn write_one(file: &Rendered) -> Result<(), ExportError> {
    let fail = |source| {
        tracing::warn!(path = %file.path.display(), error = %source, "tokens write failed");
        ExportError::Write {
            path: file.path.clone(),
            source,
        }
    };
    if let Some(parent) = file.path.parent() {
        std::fs::create_dir_all(parent).map_err(fail)?;
    }
    gob_fs::write_atomic(&file.path, file.content.as_bytes()).map_err(fail)?;
    tracing::info!(target = %file.target, path = %file.path.display(), "token file written");
    Ok(())
}

/// A same-named file at the resolution base this key does NOT use is the signature of a config
/// moved between tables, leaving a stale committed copy behind. Never an error.
pub(super) fn orphan_warnings(spec: &DesignSpec, files: &[Rendered]) -> Vec<String> {
    let mut warnings = Vec::new();
    for file in files {
        let other_base = if file.target == Target::Css {
            spec.root.clone()
        } else {
            spec.css_root()
        };
        let Some(name) = file.path.file_name() else {
            continue;
        };
        let other = other_base.join(name);
        if other.is_file() && !same_file(&other, &file.path) {
            let message = format!(
                "possibly orphaned generated copy at {}; this key resolves against {}",
                other.display(),
                file.path.parent().unwrap_or(Path::new("")).display()
            );
            tracing::warn!("{message}");
            warnings.push(message);
        }
    }
    warnings
}

fn same_file(a: &Path, b: &Path) -> bool {
    match (gob_exec::canonical(a), gob_exec::canonical(b)) {
        (Ok(a), Ok(b)) => a == b,
        _ => a == b,
    }
}
