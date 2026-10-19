//! The user trust store (security.md 2.3): MAC'd entries in `$XDG_CONFIG_HOME/gob/trust.toml`.
//!
//! An entry grants one subject (for example a pack tree digest) to one
//! repository identity (canonical root path, root commit id and remote URL; all
//! must match). Each entry records who granted it, when, and an expiry (90
//! days; 180 for network grants), and carries a keyed-blake3 MAC under the
//! per-machine key. A line that is not a well-formed, MAC-verified entry is
//! inert: it never grants anything and `doctor` counts it. Callers pass the
//! current time in; this crate never reads the wall clock.

mod entry;
mod error;
mod file;

pub use entry::{DEFAULT_TTL_SECS, Entry, Expiry, NETWORK_TTL_SECS, RepoIdentity};
pub use error::StoreError;

use std::path::{Path, PathBuf};

use crate::key::MachineKey;

/// What consulting the store says about a subject in a repository.
#[derive(Debug, PartialEq, Eq)]
pub enum Verdict<'a> {
    /// A live, verified entry matches identity and subject.
    Trusted(&'a Entry),
    /// A verified entry matches but has expired; it grants nothing.
    Expired(&'a Entry),
    /// No verified entry matches.
    Untrusted,
}

/// One thing `doctor` reports about the store.
#[derive(Debug, PartialEq, Eq)]
pub enum Finding {
    /// A verified entry is past its expiry.
    ExpiredEntry {
        /// Entry id (see [`Entry::id`]).
        id: String,
        /// The subject it covered.
        subject: String,
    },
    /// The store file is group- or world-writable (Unix permission bits).
    WritableStore {
        /// Low 12 permission bits.
        mode: u32,
    },
    /// Lines in the file that are not verified entries (hand-added or tampered).
    InertLines {
        /// How many.
        count: usize,
    },
}

/// The loaded trust store; mutations are written back atomically with owner-only permissions.
#[derive(Debug)]
pub struct TrustStore {
    path: PathBuf,
    key: MachineKey,
    entries: Vec<Entry>,
    inert: usize,
}

/// Default location: `<config>/gob/trust.toml`, beside the machine key.
///
/// # Errors
/// [`StoreError::Trust`] when no config directory is derivable.
pub fn default_store_path() -> Result<PathBuf, StoreError> {
    let key = crate::key::default_key_path()?;
    Ok(key.with_file_name("trust.toml"))
}

impl TrustStore {
    /// Load the store at `path` (missing file means empty), keeping only entries whose MAC verifies.
    ///
    /// # Errors
    /// [`StoreError::Trust`] when the file exists but cannot be read.
    pub fn open(path: &Path, key: MachineKey) -> Result<Self, StoreError> {
        let (entries, inert) = file::load(path, &key)?;
        tracing::debug!(path = %path.display(), entries = entries.len(), inert, "trust store opened");
        Ok(Self {
            path: path.to_owned(),
            key,
            entries,
            inert,
        })
    }

    /// Record a grant of `subject` to `identity` by `who` at `now` (unix seconds); returns its id.
    ///
    /// # Errors
    /// [`StoreError::BadField`] for a field with control characters; [`StoreError::Trust`] on write failure.
    pub fn grant(
        &mut self,
        identity: RepoIdentity,
        subject: &str,
        who: &str,
        now: u64,
        network: bool,
    ) -> Result<String, StoreError> {
        let e = Entry::new(&self.key, identity, subject, who, now, network)?;
        let id = e.id();
        self.entries
            .retain(|o| !(o.identity() == e.identity() && o.subject() == e.subject()));
        self.entries.push(e);
        self.save()?;
        tracing::info!(id, network, "trust granted");
        Ok(id)
    }

    /// Consult the store for `subject` in the repository `identity` at `now`.
    pub fn consult(&self, identity: &RepoIdentity, subject: &str, now: u64) -> Verdict<'_> {
        match self
            .entries
            .iter()
            .find(|e| e.identity() == identity && e.subject() == subject)
        {
            None => Verdict::Untrusted,
            Some(e) if e.expiry(now) == Expiry::Expired => {
                tracing::info!(id = e.id(), "trust entry expired");
                Verdict::Expired(e)
            }
            Some(e) => Verdict::Trusted(e),
        }
    }

    /// Every verified entry with its expiry state at `now`.
    pub fn list(&self, now: u64) -> Vec<(&Entry, Expiry)> {
        self.entries.iter().map(|e| (e, e.expiry(now))).collect()
    }

    /// Remove the entry with `id`; `Ok(false)` when none matched.
    ///
    /// # Errors
    /// [`StoreError::Trust`] on write failure.
    pub fn revoke(&mut self, id: &str) -> Result<bool, StoreError> {
        let before = self.entries.len();
        self.entries.retain(|e| e.id() != id);
        let removed = self.entries.len() != before;
        if removed {
            self.save()?;
            tracing::info!(id, "trust revoked");
        }
        Ok(removed)
    }

    /// What `doctor` should report: expired entries, a writable store, inert lines.
    pub fn doctor(&self, now: u64) -> Vec<Finding> {
        let mut out: Vec<Finding> = self
            .entries
            .iter()
            .filter(|e| e.expiry(now) == Expiry::Expired)
            .map(|e| Finding::ExpiredEntry {
                id: e.id(),
                subject: e.subject().to_owned(),
            })
            .collect();
        if let Some(mode) = file::writable_mode(&self.path) {
            out.push(Finding::WritableStore { mode });
        }
        if self.inert > 0 {
            out.push(Finding::InertLines { count: self.inert });
        }
        out
    }

    fn save(&mut self) -> Result<(), StoreError> {
        file::save(&self.path, &self.entries)?;
        self.inert = 0;
        Ok(())
    }
}
