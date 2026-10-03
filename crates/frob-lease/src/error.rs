//! Lease failures and their mapping to CLI refusals.

use std::path::PathBuf;

use frob_ledger::TicketId;
use frob_ledger::model::Stamp;
use gob_diagnostics::{Refusal, RefusalClass};

use crate::model::Holder;

/// The `overlap` text of a [`LeaseError::Held`] caused by the ticket's own lease rather than a scope collision.
pub const SAME_TICKET: &str = "the ticket itself";

/// Why a lease operation did not happen.
#[derive(Debug, thiserror::Error)]
pub enum LeaseError {
    /// Another holder owns a lease that overlaps (or the ticket's own lease).
    #[error(
        "E-LEASE-HELD: ticket {ticket} is leased by {holder} since {since}; overlap: {overlap}"
    )]
    Held {
        /// The holder of the blocking lease.
        holder: Holder,
        /// The ticket the blocking lease belongs to.
        ticket: TicketId,
        /// When the blocking lease was taken.
        since: Stamp,
        /// The globs or files that collide, comma separated.
        overlap: String,
    },
    /// The holder already owns its limit of live leases.
    #[error("E-LEASE-WIP: {holder} already holds {count} live leases (limit {limit})")]
    WipLimit {
        /// The holder asking for one more.
        holder: Holder,
        /// Live leases it holds.
        count: usize,
        /// The configured limit.
        limit: u32,
    },
    /// The ticket has no lease (renew, steal).
    #[error("E-LEASE-NONE: ticket {ticket} holds no live lease")]
    NotHeld {
        /// The ticket asked about.
        ticket: TicketId,
    },
    /// The lock file stayed busy for the whole wait.
    #[error("E-LEASE-LOCK-TIMEOUT: {} stayed locked for {waited_ms} ms", path.display())]
    LockTimeout {
        /// The lock file.
        path: PathBuf,
        /// Milliseconds waited.
        waited_ms: u64,
    },
    /// A scope entry is not a valid glob.
    #[error("E-LEASE-GLOB: `{glob}` is not a valid glob: {message}")]
    BadGlob {
        /// The offending entry.
        glob: String,
        /// The parser's complaint.
        message: String,
    },
    /// A requested glob would cover other tickets' changelog fragments.
    #[error(
        "E-LEASE-FRAGMENT-GLOB: `{glob}` would cover other tickets' changelog fragments and block them; a ticket's own `changelog.d/<ULID>.<type>.md` needs no lease, so drop this glob (write the fragment with `frob ticket fragment`)"
    )]
    FragmentGlob {
        /// The refused glob.
        glob: String,
    },
    /// A lease file exists but cannot be read as a lease.
    #[error("E-LEASE-FORMAT: {}: {message}", path.display())]
    Format {
        /// The lease file.
        path: PathBuf,
        /// What is wrong.
        message: String,
    },
    /// Reading or writing the lease directory failed.
    #[error("E-LEASE-IO: {context}: {source}")]
    Io {
        /// What was being done.
        context: String,
        /// The OS error.
        source: std::io::Error,
    },
    /// Resolving scope globs against the repository failed.
    #[error("E-LEASE-WALK: {0}")]
    Walk(String),
    /// The repository or its config could not be opened.
    #[error("E-LEASE-REPO: {0}")]
    Repo(String),
}

impl LeaseError {
    /// Wrap an I/O error with what was being done.
    pub fn io(context: impl Into<String>, source: std::io::Error) -> Self {
        Self::Io {
            context: context.into(),
            source,
        }
    }

    /// The caller-visible refusal for this failure, without a remedy; `None` for bugs and environment faults.
    pub fn to_refusal(&self) -> Option<Refusal> {
        use RefusalClass::{GuardNeedsAction, GuardRetryByWaiting, Timeout};
        let code = match self {
            Self::Held { .. } => ("E-LEASE-HELD", GuardRetryByWaiting),
            Self::WipLimit { .. } => ("E-LEASE-WIP", GuardNeedsAction),
            Self::NotHeld { .. } => ("E-LEASE-NONE", GuardNeedsAction),
            Self::LockTimeout { .. } => ("E-LEASE-LOCK-TIMEOUT", Timeout),
            Self::BadGlob { .. } => ("E-LEASE-GLOB", GuardNeedsAction),
            Self::FragmentGlob { .. } => ("E-LEASE-FRAGMENT-GLOB", GuardNeedsAction),
            Self::Format { .. } => ("E-LEASE-FORMAT", GuardNeedsAction),
            Self::Io { .. } | Self::Walk(_) | Self::Repo(_) => return None,
        };
        let message = self.to_string();
        let message = message
            .split_once(": ")
            .map_or(message.as_str(), |(_, m)| m);
        Some(Refusal::new(code.0, code.1, message))
    }
}
