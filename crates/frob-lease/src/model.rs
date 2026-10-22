//! The lease file: who holds which scope, since when, and how it changed hands.

use gob_path::Shown;
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
        write!(f, "{} in {}", self.actor, Shown::of(&self.worktree))
    }
}

/// One takeover or rescope of a lease, kept in the lease file as history.
///
/// A rescope by the holder has `from == to` and a reason starting `rescope:`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct StealRecord {
    /// When the lease changed.
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
    /// Takeovers and rescopes, oldest first.
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    pub history: Vec<StealRecord>,
    /// True while the ticket waits on the land train: the holder handed it off, so it no longer counts toward WIP.
    #[serde(default, skip_serializing_if = "std::ops::Not::not")]
    pub queued: bool,
    /// The `FROB_AGENT` label when an agent took the claim (selects the short agent window); absent for a human.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub agent: Option<String>,
    /// When the holder last ran `frob claim touch` (a soft heartbeat).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub touched_at: Option<Stamp>,
    /// The note given to the last `frob claim touch`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub touch_note: Option<String>,
    /// Commit `work --here` was started from: the diff base for `check --ticket` and `test` on a shared checkout.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub base: Option<String>,
}

impl Lease {
    /// The holder kind that fixes this claim's idle window (agent when an agent label was recorded).
    #[must_use]
    pub fn holder_kind(&self) -> frob_ledger::claim_window::HolderKind {
        frob_ledger::claim_agent::holder_kind(self.agent.as_deref())
    }

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

/// A queued request for a scope that a live lease blocks, stored as `<ticket>.toml` in the waiters directory (frob:ticket 01M41ZRNYEWRY4V2MXT3WMXBBJ).
///
/// The waiter heartbeats while its `work --wait` process lives; a record not renewed for `ttl_secs` is dropped.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
pub struct Waiter {
    /// The ticket waiting for its lease.
    pub ticket: TicketId,
    /// Who will hold the lease once granted.
    pub holder: Holder,
    /// Glob patterns the waiter needs free.
    pub scope: Vec<String>,
    /// When the waiter joined the queue (FIFO order key).
    pub enqueued_at: Stamp,
    /// Last heartbeat of the waiting process.
    pub renewed_at: Stamp,
    /// Seconds after `renewed_at` at which the waiter is presumed dead.
    pub ttl_secs: u64,
}

impl Waiter {
    /// True while `now` is before the heartbeat expiry.
    pub fn is_live(&self, now: Stamp) -> bool {
        let ttl = i64::try_from(self.ttl_secs).unwrap_or(i64::MAX);
        now.unix() < self.renewed_at.unix().saturating_add(ttl)
    }

    /// Whole seconds spent in the queue as of `now`.
    pub fn age_secs(&self, now: Stamp) -> i64 {
        (now.unix() - self.enqueued_at.unix()).max(0)
    }
}
