//! `trust --follow REF` (security.md 2.3): trust the pairs a fetched protected branch carries.
//!
//! This module is pure. A [`FollowRecord`] is what the one-time ceremony
//! stores: the full refname, the remote URL and the recorded tip. The tip only
//! moves through [`FollowRecord::advance`], which the caller invokes after a
//! frob-performed fast-forward fetch from the recorded URL; any other move is
//! refused. Trust is evaluated at `merge-base(HEAD, recorded tip)`: the caller
//! reads the pack lock at that commit from git objects and hands the text to
//! [`FollowTrust::from_lock_toml`]. A pair present only in an unpushed commit
//! is not in that lock, so it is untrusted; no prompt is involved.

// frob:ticket 01M3ZX7V9AKM8KVBHF32BWEC3K

use tracing::{info, warn};

use crate::baseref::{BaseRefError, BaseRefTrust, BaseRefVerdict};

/// Why a follow record could not be created or advanced.
#[derive(Debug, thiserror::Error, PartialEq, Eq)]
pub enum FollowError {
    /// The refname is not a full `refs/remotes/...` or `refs/heads/...` name.
    #[error("E-TRUST-FOLLOW-REF: `{0}` is not a full refname (refs/remotes/<remote>/<branch>)")]
    NotFullRef(String),
    /// The new tip is not a fast-forward of the recorded tip, or was not fetched by frob.
    #[error(
        "E-TRUST-FOLLOW-MOVED: ref {refname} moved from {from} to {to} without a frob fast-forward fetch; ignored"
    )]
    Moved {
        /// The followed ref.
        refname: String,
        /// The recorded tip.
        from: String,
        /// The offered tip.
        to: String,
    },
}

/// The recorded follow ceremony: ref, remote URL and tip.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct FollowRecord {
    refname: String,
    url: String,
    tip: String,
}

impl FollowRecord {
    /// Records following `refname` at `tip` from `url`.
    ///
    /// # Errors
    /// [`FollowError::NotFullRef`] when `refname` is not a full ref.
    pub fn new(refname: &str, url: &str, tip: &str) -> Result<Self, FollowError> {
        if !refname.starts_with("refs/remotes/") && !refname.starts_with("refs/heads/") {
            warn!(refname, "follow refused: not a full refname");
            return Err(FollowError::NotFullRef(refname.to_owned()));
        }
        info!(refname, url, tip, "follow recorded");
        Ok(Self {
            refname: refname.to_owned(),
            url: url.to_owned(),
            tip: tip.to_owned(),
        })
    }

    /// The followed full refname.
    #[must_use]
    pub fn refname(&self) -> &str {
        &self.refname
    }

    /// The remote URL recorded at the ceremony.
    #[must_use]
    pub fn url(&self) -> &str {
        &self.url
    }

    /// The recorded tip commit id.
    #[must_use]
    pub fn tip(&self) -> &str {
        &self.tip
    }

    /// Moves the tip to `new_tip` only for a frob fast-forward fetch; anything else is refused.
    ///
    /// # Errors
    /// [`FollowError::Moved`] when `fast_forward_by_frob` is false.
    pub fn advance(&self, new_tip: &str, fast_forward_by_frob: bool) -> Result<Self, FollowError> {
        if !fast_forward_by_frob {
            warn!(refname = %self.refname, "followed ref moved outside a frob fast-forward; ignored");
            return Err(FollowError::Moved {
                refname: self.refname.clone(),
                from: self.tip.clone(),
                to: new_tip.to_owned(),
            });
        }
        info!(refname = %self.refname, new_tip, "followed tip advanced");
        Ok(Self {
            tip: new_tip.to_owned(),
            ..self.clone()
        })
    }
}

/// The pairs trusted by following: those in the lock at `merge-base(HEAD, tip)`.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct FollowTrust {
    pairs: BaseRefTrust,
}

impl FollowTrust {
    /// Trust nothing: the merge-base has no lock.
    #[must_use]
    pub fn empty() -> Self {
        Self::default()
    }

    /// Parses the pack lock text read at the merge-base of HEAD and the recorded tip.
    ///
    /// # Errors
    /// [`BaseRefError::Malformed`] when the text is not a lock-shaped TOML document.
    pub fn from_lock_toml(text: &str) -> Result<Self, BaseRefError> {
        Ok(Self {
            pairs: BaseRefTrust::from_lock_toml(text)?,
        })
    }

    /// Decides the live pack `name` with tree digest `tree`; no prompt, no store write.
    #[must_use]
    pub fn decide(&self, name: &str, tree: &str) -> BaseRefVerdict {
        self.pairs.decide(name, tree)
    }
}
