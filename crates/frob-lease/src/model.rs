//! The lease file: who holds which scope, since when, and how it changed hands.

use std::path::PathBuf;

use frob_ledger::TicketId;
use frob_ledger::model::Stamp;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// Who holds a lease: an actor working from one worktree (decision D26).
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize, JsonSchema)]
pub struct Holder {
    /// The identity recorded on ledger events.
    pub actor: String,
    /// Absolute path of the worktree the holder works in.
    pub worktree: PathBuf,
}

impl std::fmt::Display for Holder {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{} in {}", self.actor, self.worktree.display())
    }
}

/// One takeover of a lease, kept in the lease file as history.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct StealRecord {
    /// When the lease was taken over.
    pub at: Stamp,
    /// The holder it was taken from.
    pub from: Holder,
    /// The holder it went to.
    pub to: Holder,
    /// Why the caller said it was stale.
    pub reason: String,
}

/// A write lease on a ticket's scope, stored as `<ticket>.toml`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Lease {
    /// The ticket the lease belongs to.
    pub ticket: TicketId,
    /// The current holder.
    pub holder: Holder,
    /// Glob patterns the holder may write.
    pub scope: Vec<String>,
    /// When the current holder took the lease.
    pub acquired_at: Stamp,
    /// Last heartbeat.
    pub renewed_at: Stamp,
    /// Seconds after `renewed_at` at which the lease expires.
    pub ttl_secs: u64,
    /// Takeovers, oldest first.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub history: Vec<StealRecord>,
}

impl Lease {
    /// Unix second at which the lease expires.
    pub fn expires_at(&self) -> i64 {
        self.renewed_at
            .unix()
            .saturating_add(i64::try_from(self.ttl_secs).unwrap_or(i64::MAX))
    }

    /// True while `now` is before the expiry.
    pub fn is_live(&self, now: Stamp) -> bool {
        now.unix() < self.expires_at()
    }
}
