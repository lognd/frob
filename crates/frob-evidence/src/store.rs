//! The blob store: inline under the threshold, the `dir:` store above it.
//!
//! Blobs are addressed by blake3 hex. Milestone 1 supports exactly `dir:` and
//! `https://` stores (tickets.md section 9, audit M35): `dir:` blobs live under
//! `.git/frob/artifacts` by default (outside `.frob/`, non-authoritative), and
//! `https://` URIs are recorded but never downloaded or uploaded.

use std::path::{Path, PathBuf};

use gob_git::Repo;

use crate::config::EvidenceTable;
use crate::error::{EvidenceError, Result};
use crate::record::digest_hex;

/// Store schemes of later milestones, rejected with a clear message.
const UNSUPPORTED: &[&str] = &["gh-artifact:", "gh-release:", "s3:", "gcs:"];

/// Where a stored blob can be found again.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Stored {
    /// Small enough to live in the event file.
    Inline(String),
    /// In a store; the event carries this URI.
    Uri(String),
}

/// The result of fetching a blob by URI.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Fetched {
    /// The verified bytes.
    Found(Vec<u8>),
    /// The blob cannot be measured now (missing, expired, corrupt or not downloadable).
    Unmeasured {
        /// The URI that was asked for.
        uri: String,
        /// Why it is unmeasured.
        reason: String,
    },
}

#[derive(Debug, Clone)]
enum Target {
    Dir { rel: String },
    Https { base: String },
}

/// The configured store plus the repository paths relative locations resolve against.
#[derive(Debug, Clone)]
pub struct BlobStore {
    target: Target,
    inline_max: usize,
    work_dir: Option<PathBuf>,
    common_dir: PathBuf,
}

impl BlobStore {
    /// Build the store described by `cfg` for `repo`.
    ///
    /// # Errors
    ///
    /// [`EvidenceError::Config`] for a store scheme other than `dir:` or `https://`.
    pub fn open(cfg: &EvidenceTable, repo: &Repo) -> Result<Self> {
        let raw = cfg.store.trim();
        let target = if raw.starts_with("https://") {
            Target::Https {
                base: raw.trim_end_matches('/').to_owned(),
            }
        } else if let Some(rel) = raw.strip_prefix("dir:") {
            Target::Dir {
                rel: rel.trim_end_matches('/').to_owned(),
            }
        } else if raw.contains("://") || UNSUPPORTED.iter().any(|p| raw.starts_with(p)) {
            return Err(EvidenceError::Config(format!(
                "store `{raw}` is not supported in milestone 1; use `dir:<path>` or an https URL"
            )));
        } else {
            Target::Dir {
                rel: raw.trim_end_matches('/').to_owned(),
            }
        };
        if matches!(&target, Target::Dir { rel } if rel.is_empty()) {
            return Err(EvidenceError::Config("store directory is empty".to_owned()));
        }
        let inline_max = usize::try_from(cfg.inline_max_bytes).unwrap_or(usize::MAX);
        tracing::debug!(store = raw, inline_max, "blob store opened");
        Ok(Self {
            target,
            inline_max,
            work_dir: repo.work_dir().map(Path::to_path_buf),
            common_dir: repo.common_dir().to_path_buf(),
        })
    }

    /// Resolve a `dir:` path: absolute as is, `.git/...` under the common dir, else under the work tree.
    fn resolve(&self, rel: &str) -> PathBuf {
        let path = Path::new(rel);
        if path.is_absolute() {
            return path.to_path_buf();
        }
        if let Some(rest) = rel.strip_prefix(".git/") {
            return self.common_dir.join(rest);
        }
        self.work_dir
            .as_deref()
            .unwrap_or(&self.common_dir)
            .join(rel)
    }

    /// Store `text`: inline when within the threshold, else in the store.
    ///
    /// With an `https://` store nothing is uploaded in milestone 1, so oversized
    /// text stays inline (and a warning is logged).
    ///
    /// # Errors
    ///
    /// [`EvidenceError::Io`] when the `dir:` store cannot be written.
    pub fn put(&self, text: &str) -> Result<Stored> {
        if text.len() <= self.inline_max {
            tracing::debug!(bytes = text.len(), "evidence stored inline");
            return Ok(Stored::Inline(text.to_owned()));
        }
        match &self.target {
            Target::Https { base } => {
                tracing::warn!(
                    base,
                    bytes = text.len(),
                    "https store is record-only in milestone 1; keeping the transcript inline"
                );
                Ok(Stored::Inline(text.to_owned()))
            }
            Target::Dir { rel } => {
                let hex = digest_hex(text.as_bytes());
                let dir = self.resolve(rel);
                let path = dir.join(&hex);
                if path.is_file() {
                    tracing::debug!(path = %path.display(), "blob already stored");
                } else {
                    std::fs::create_dir_all(&dir).map_err(|e| EvidenceError::io(&dir, e))?;
                    let tmp = dir.join(format!(".{hex}.tmp"));
                    std::fs::write(&tmp, text.as_bytes())
                        .map_err(|e| EvidenceError::io(&tmp, e))?;
                    std::fs::rename(&tmp, &path).map_err(|e| EvidenceError::io(&path, e))?;
                    tracing::info!(path = %path.display(), bytes = text.len(), "blob stored");
                }
                Ok(Stored::Uri(format!("dir:{rel}/{hex}")))
            }
        }
    }

    /// Fetch the blob at `uri`; a missing blob (or an https URI) is `Unmeasured`, never an error.
    pub fn fetch(&self, uri: &str) -> Fetched {
        let Some(rel) = uri.strip_prefix("dir:") else {
            let reason = if uri.starts_with("https://") {
                "https artifacts are recorded only in milestone 1 (no download)"
            } else {
                "unsupported store scheme"
            };
            tracing::debug!(uri, reason, "blob not fetchable");
            return Fetched::Unmeasured {
                uri: uri.to_owned(),
                reason: reason.to_owned(),
            };
        };
        let path = self.resolve(rel);
        match std::fs::read(&path) {
            Ok(bytes) => Fetched::Found(bytes),
            Err(e) => {
                tracing::info!(uri, path = %path.display(), error = %e, "blob missing; evidence is unmeasured");
                Fetched::Unmeasured {
                    uri: uri.to_owned(),
                    reason: format!("blob missing: {e}"),
                }
            }
        }
    }

    /// [`Self::fetch`] plus a blake3 check against `digest`; a mismatch is `Unmeasured`.
    pub fn fetch_verified(&self, uri: &str, digest: &str) -> Fetched {
        match self.fetch(uri) {
            Fetched::Found(bytes) if digest_hex(&bytes) != digest => {
                tracing::warn!(uri, "blob does not match its recorded digest");
                Fetched::Unmeasured {
                    uri: uri.to_owned(),
                    reason: "blob does not match its recorded digest".to_owned(),
                }
            }
            other => other,
        }
    }
}
