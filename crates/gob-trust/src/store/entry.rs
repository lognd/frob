//! One MAC'd trust entry and the repository identity it is bound to.

use std::path::{Path, PathBuf};

use super::error::StoreError;
use crate::key::MachineKey;
use crate::mac::{Canonical, CanonicalWriter, Tag, mac_record, verify_record};

/// Default entry lifetime: 90 days.
pub const DEFAULT_TTL_SECS: u64 = 90 * 86_400;
/// Lifetime of grants of network effects: 180 days.
pub const NETWORK_TTL_SECS: u64 = 180 * 86_400;
const CONTEXT: &str = "gob-trust-entry/v1";

/// Who a grant applies to: canonical root path, root commit id and remote URL must all match.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RepoIdentity {
    /// Canonical repository root.
    pub root: PathBuf,
    /// Id of the repository's root commit.
    pub root_commit: String,
    /// Remote URL (empty when there is none).
    pub remote_url: String,
}

/// Whether an entry still grants at a given time.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Expiry {
    /// Still in force.
    Live,
    /// Past its expiry.
    Expired,
}

/// A verified grant of `subject` to a repository identity.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct Entry {
    identity: RepoIdentity,
    subject: String,
    who: String,
    granted_at: u64,
    expires_at: u64,
    network: bool,
    tag: Tag,
}

/// The authenticated fields of an entry (everything but the tag).
pub(super) struct Body<'a> {
    pub identity: &'a RepoIdentity,
    pub subject: &'a str,
    pub who: &'a str,
    pub granted_at: u64,
    pub expires_at: u64,
    pub network: bool,
}

impl Canonical for Body<'_> {
    fn write_canonical(&self, w: &mut CanonicalWriter) {
        w.str(self.subject)
            .str(self.who)
            .u64(self.granted_at)
            .u64(self.expires_at)
            .u64(u64::from(self.network))
            .str(&gob_path::Shown::with_home(&self.identity.root, None).to_string())
            .str(&self.identity.root_commit)
            .str(&self.identity.remote_url);
    }
}

fn single_line(field: &'static str, s: &str) -> Result<(), StoreError> {
    if s.chars().any(char::is_control) {
        Err(StoreError::BadField(field))
    } else {
        Ok(())
    }
}

impl Entry {
    /// Build and MAC a new entry; expiry is 90 days, or 180 for `network` grants.
    pub(super) fn new(
        key: &MachineKey,
        identity: RepoIdentity,
        subject: &str,
        who: &str,
        now: u64,
        network: bool,
    ) -> Result<Self, StoreError> {
        single_line("subject", subject)?;
        single_line("who", who)?;
        single_line("root_commit", &identity.root_commit)?;
        single_line("remote_url", &identity.remote_url)?;
        if gob_path::exact_text(&identity.root).is_none_or(|s| s.chars().any(char::is_control)) {
            return Err(StoreError::BadField("root"));
        }
        let ttl = if network {
            NETWORK_TTL_SECS
        } else {
            DEFAULT_TTL_SECS
        };
        let expires_at = now.saturating_add(ttl);
        let tag = mac_record(
            key,
            CONTEXT,
            &Body {
                identity: &identity,
                subject,
                who,
                granted_at: now,
                expires_at,
                network,
            },
        );
        Ok(Self {
            identity,
            subject: subject.to_owned(),
            who: who.to_owned(),
            granted_at: now,
            expires_at,
            network,
            tag,
        })
    }

    /// Rebuild a parsed entry, keeping it only when the MAC verifies under `key`.
    pub(super) fn from_parts(
        key: &MachineKey,
        identity: RepoIdentity,
        subject: String,
        who: String,
        times: (u64, u64),
        network: bool,
        tag: Tag,
    ) -> Option<Self> {
        let body = Body {
            identity: &identity,
            subject: &subject,
            who: &who,
            granted_at: times.0,
            expires_at: times.1,
            network,
        };
        verify_record(key, CONTEXT, &body, &tag).ok()?;
        Some(Self {
            identity,
            subject,
            who,
            granted_at: times.0,
            expires_at: times.1,
            network,
            tag,
        })
    }

    /// Short stable id (prefix of the MAC) used by `trust revoke`.
    pub fn id(&self) -> String {
        self.tag.to_hex()[..12].to_owned()
    }

    /// The repository identity this entry is bound to.
    pub fn identity(&self) -> &RepoIdentity {
        &self.identity
    }

    /// What was granted (for example a pack tree digest).
    pub fn subject(&self) -> &str {
        &self.subject
    }

    /// Who granted it.
    pub fn who(&self) -> &str {
        &self.who
    }

    /// Grant time, unix seconds.
    pub fn granted_at(&self) -> u64 {
        self.granted_at
    }

    /// Expiry time, unix seconds.
    pub fn expires_at(&self) -> u64 {
        self.expires_at
    }

    /// Whether this grants network effects (180-day lifetime).
    pub fn network(&self) -> bool {
        self.network
    }

    /// Whether the entry is live or expired at `now`.
    pub fn expiry(&self, now: u64) -> Expiry {
        if now >= self.expires_at {
            Expiry::Expired
        } else {
            Expiry::Live
        }
    }

    pub(super) fn tag(&self) -> &Tag {
        &self.tag
    }

    /// The repository root as a path.
    pub fn root(&self) -> &Path {
        &self.identity.root
    }
}
