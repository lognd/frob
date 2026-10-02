//! The lock file model, its TOML form and atomic persistence.

use std::collections::BTreeMap;
use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};

/// The on-disk format version this crate reads and writes.
pub const LOCK_VERSION: u32 = 1;

/// The lock file name of `product` (`frob` gives `frob.lock`).
pub fn file_name(product: &str) -> String {
    format!("{product}.lock")
}

/// Why a lock file could not be read, parsed or written.
#[derive(Debug, thiserror::Error)]
pub enum LockError {
    /// The file could not be read or written.
    #[error("E-LOCK-IO: {context} {path}: {source}")]
    Io {
        /// What was being attempted.
        context: &'static str,
        /// The file involved.
        path: PathBuf,
        /// The OS error.
        source: std::io::Error,
    },
    /// The file is not valid lock TOML.
    #[error("E-LOCK-PARSE: {path}: {message}")]
    Parse {
        /// The file (or `<memory>`).
        path: PathBuf,
        /// The parser message.
        message: String,
    },
    /// The file was written by a newer format version.
    #[error("E-LOCK-VERSION: {path} has version {found}, this build reads {LOCK_VERSION}")]
    Version {
        /// The file.
        path: PathBuf,
        /// The version found.
        found: u32,
    },
    /// The in-memory lock could not be rendered as TOML (a bug).
    #[error("E-LOCK-RENDER: {0}")]
    Render(String),
}

/// A bound doc section and its digest at ack time.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LockTarget {
    /// The `path#slug` of the doc section.
    #[serde(rename = "ref")]
    pub target: String,
    /// Hex digest of that section when acknowledged.
    pub digest: String,
}

/// One acknowledged symbol.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LockEntry {
    /// Hex digest of the signature facet.
    pub sig: String,
    /// Hex digest of the body facet.
    pub body: String,
    /// Hex digest of the doc-comment facet.
    pub doc: String,
    /// Who acknowledged (`Name <email>` or `unknown`).
    pub acked_by: String,
    /// When (RFC 3339, UTC).
    pub acked_at: String,
    /// Why, when the actor gave a reason.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub reason: Option<String>,
    /// Doc sections bound to the symbol, sorted by `target`.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub targets: Vec<LockTarget>,
}

impl LockEntry {
    /// An entry with the three digests and the actor and time, no reason or targets.
    pub fn new(sig: &str, body: &str, doc: &str, acked_by: &str, acked_at: &str) -> Self {
        Self {
            sig: sig.to_owned(),
            body: body.to_owned(),
            doc: doc.to_owned(),
            acked_by: acked_by.to_owned(),
            acked_at: acked_at.to_owned(),
            reason: None,
            targets: Vec::new(),
        }
    }

    /// The recorded digest of doc section `target`, if one was bound at ack time.
    pub fn target_digest(&self, target: &str) -> Option<&str> {
        self.targets
            .iter()
            .find(|t| t.target == target)
            .map(|t| t.digest.as_str())
    }
}

/// A whole lock file: a version and entries keyed by symref string.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct LockFile {
    /// Format version, always [`LOCK_VERSION`] when written.
    pub version: u32,
    /// Entries in symref order.
    #[serde(default)]
    pub entries: BTreeMap<String, LockEntry>,
}

impl Default for LockFile {
    fn default() -> Self {
        Self {
            version: LOCK_VERSION,
            entries: BTreeMap::new(),
        }
    }
}

impl LockFile {
    /// Parses lock TOML; `origin` names the file in errors.
    ///
    /// # Errors
    ///
    /// [`LockError::Parse`] for malformed TOML, [`LockError::Version`] for a newer format.
    pub fn parse(text: &str, origin: &Path) -> Result<Self, LockError> {
        let lock: Self = toml::from_str(text).map_err(|e| LockError::Parse {
            path: origin.to_path_buf(),
            message: e.to_string(),
        })?;
        if lock.version > LOCK_VERSION {
            return Err(LockError::Version {
                path: origin.to_path_buf(),
                found: lock.version,
            });
        }
        Ok(lock)
    }

    /// Parses lock TOML held in memory.
    ///
    /// # Errors
    ///
    /// As [`LockFile::parse`].
    pub fn from_toml(text: &str) -> Result<Self, LockError> {
        Self::parse(text, Path::new("<memory>"))
    }

    /// Renders stable TOML: sorted entries, trailing newline.
    ///
    /// # Errors
    ///
    /// [`LockError::Render`] if serialization fails (a bug).
    pub fn to_toml(&self) -> Result<String, LockError> {
        let mut text = toml::to_string(self).map_err(|e| LockError::Render(e.to_string()))?;
        if !text.ends_with('\n') {
            text.push('\n');
        }
        Ok(text)
    }

    /// Reads `path`; a missing file is an empty lock, not an error.
    ///
    /// # Errors
    ///
    /// [`LockError::Io`] for read failures other than not-found, plus parse errors.
    pub fn load(path: &Path) -> Result<Self, LockError> {
        match std::fs::read_to_string(path) {
            Ok(text) => {
                let lock = Self::parse(&text, path)?;
                tracing::debug!(path = %path.display(), entries = lock.entries.len(), "lock loaded");
                Ok(lock)
            }
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                tracing::debug!(path = %path.display(), "no lock file; empty lock");
                Ok(Self::default())
            }
            Err(source) => Err(LockError::Io {
                context: "read",
                path: path.to_path_buf(),
                source,
            }),
        }
    }

    /// Writes `path` atomically (sibling temp file, then rename).
    ///
    /// # Errors
    ///
    /// [`LockError::Io`] when the temp file cannot be written or renamed, plus render errors.
    pub fn save(&self, path: &Path) -> Result<(), LockError> {
        let text = self.to_toml()?;
        let mut tmp = path.as_os_str().to_owned();
        tmp.push(".tmp");
        let tmp = PathBuf::from(tmp);
        let io = |context, p: &Path| {
            let p = p.to_path_buf();
            move |source| LockError::Io {
                context,
                path: p,
                source,
            }
        };
        std::fs::write(&tmp, text).map_err(io("write", &tmp))?;
        std::fs::rename(&tmp, path).map_err(io("rename", path))?;
        tracing::info!(path = %path.display(), entries = self.entries.len(), "lock saved");
        Ok(())
    }
}
