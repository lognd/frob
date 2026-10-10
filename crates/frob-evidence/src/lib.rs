//! Evidence for frob tickets: providers, the blob store, evidence events and
//! the close guard (design: `tickets.md` section 9; decisions D36, audit M35).
//!
//! # Model
//!
//! An [`EvidenceRecord`] (provider, ref, blake3 digest, optional URI, status,
//! capture time, accepted criteria) is persisted as the body of a ledger
//! `evidence` event ([`events`]). Providers ([`provider`]) are `nextest`
//! (verdict and executed test names through `gob-exec`), `command` (an
//! allowlisted tool: exit code and transcript digest) and `file` (a hashed
//! path); `attestation` is a person's statement ([`attestation`]). Transcripts are redacted with `gob_log::redact` and their absolute local paths rewritten to placeholders ([`scrub`]); up to
//! `[evidence] inline_max_bytes` they live inline in the event, larger ones in
//! the `dir:` store ([`store`], addressed by blake3, non-authoritative) with the
//! event carrying the URI. A missing blob degrades a record to
//! [`Status::Unmeasured`], never to failed.
//!
//! # Hooks for the binary
//!
//! [`register`] adds the `ticket evidence add|list|fetch` verbs to a `gob_cli::Cli`;
//! [`EvidenceGuard`] implements `frob_ledger::guards::CloseGuard` so closing a
//! code-changing ticket needs a measured record (`E-EVIDENCE-MISSING`) unless
//! [`EvidenceGuard::allow_bypass`] was set (and recorded with
//! [`EvidenceGuard::record_bypass`]).

pub mod attestation;
pub mod config;
pub mod done;
pub mod error;
pub mod events;
pub mod guard;
pub mod provider;
pub mod record;
pub mod scrub;
pub mod store;
pub mod verbs;
pub mod workspace;

pub use config::{DotnetTable, EvidenceTable, TestsTable, UnityTable};
pub use done::DoneGuard;
pub use error::{EvidenceError, Result};
pub use guard::EvidenceGuard;
pub use record::{EvidenceRecord, Provider, Status};
pub use store::{BlobStore, Fetched, Stored};
pub use workspace::Workspace;

/// Register the `ticket evidence` verbs on `cli`, mirroring how the binary registers `ticket`.
#[must_use]
pub fn register(cli: gob_cli::Cli) -> gob_cli::Cli {
    cli.register::<verbs::AddVerb>()
        .register::<verbs::ListVerb>()
        .register::<verbs::FetchVerb>()
}

/// In-place form of [`register`] for callers that hold `&mut Cli`.
pub fn register_mut(cli: &mut gob_cli::Cli) {
    let taken = std::mem::replace(cli, gob_cli::Cli::new("frob", env!("CARGO_PKG_VERSION")));
    *cli = register(taken);
}
