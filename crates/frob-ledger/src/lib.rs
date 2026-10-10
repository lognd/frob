//! The frob ticket ledger: ULID tickets, append-only events, fold, SQLite
//! index, merge driver and the ledger rules (design: `tickets.md` sections 2
//! to 5 and 11; decisions D23, D24, D33, D34).
//!
//! # Model
//!
//! A ticket is a directory `tickets/<ulid>/` holding `ticket.md` (TOML
//! frontmatter between `+++` fences, then markdown, see [`doc`]) and
//! `events/<ulid>.toml`, one append-only [`event::Event`] per file. The
//! frontmatter is a cache: [`fold::fold`] of the events must equal it
//! (`doctor` and rule `TICK001` check exactly that). Events fold in
//! (ULID time, `at`, id) order; a `field` event carries the previous value so a
//! concurrent conflicting pair is reported, never silently picked.
//!
//! The M1 event kinds are `create`, `field`, `transition`, `comment`, `link`,
//! `exception` and `triage` (the inbox decisions of [`triage`]); every other kind of the design table parses as an
//! uninterpreted event so a newer ledger still folds. The `create` event (not in
//! the design table yet) carries a ticket's initial values; `rev` in each file
//! is the event-format revision ([`event::EVENT_REV`]).
//!
//! # Writes, reads, handles
//!
//! [`Ledger`] resolves the ledger ref (`[tickets] ref`, or the current branch in
//! `ref_mode = "branch"`), reads everything from that ref's tree, and writes
//! through `gob_git::Repo::commit_paths` (compare-and-swap, never an index).
//! Every mutation appends its events and rewrites the frontmatter in one commit
//! `tickets(<verb>): <handle> <title>`. Reads go through [`index::Index`], a
//! SQLite cache under `.frob/tickets.sqlite` keyed by the tickets tree id and
//! rebuilt when it differs. The only persisted id is the full ULID; the human
//! handle is `~` plus the shortest unique suffix of its random part (at least
//! seven characters, [`id::compute_handles`]) and every lookup accepts a full
//! ULID, a `~suffix` or an alias ([`index::Index::resolve`]).
//!
//! # Error handling: `error_set` versus `thiserror` (decision D22 trial)
//!
//! This crate declares its errors with `error_set` ([`error`]): six small sets
//! (format, fold, input, lookup, store, plus their union [`LedgerError`]) in
//! one macro block, where `thiserror` would need one enum per layer and
//! hand-written `From` impls (or a single flat enum). `error_set` derives the
//! `From` conversions between a subset and its union, so `?` composes layers
//! for free, and it names each source type once (`Git(GitError)`,
//! `Sql(rusqlite::Error)`) instead of repeating `#[from]`. Costs met: a
//! variant field that the `display` string does not mention triggers an
//! unused-variable warning in the generated code (worked around by rendering
//! it), generated items are `pub` with no way to narrow visibility, and error
//! messages cannot use `#[error(transparent)]`-style forwarding for fields. The
//! verdict is to keep it here: the union-of-sets shape matches this crate
//! exactly. The other crates keep `thiserror`, which `gob-diagnostics` already
//! needs for `Refusal`.
//!
//! # Hooks for later crates
//!
//! [`guards::CloseGuard`] is the close-guard trait (the evidence guard arrives
//! with `frob-evidence`), [`guards::LeaseCheck`] the lease hook `doable`
//! consults (`frob-lease`). [`rules`] declares `TICK001` to `TICK005` (`TICK004` is [`privacy`], a byte scan of committed ledger files, repaired by [`scrub`]; `TICK005` is the same scan for the local private terms of [`redact`]);
//! `frob-check` supplies the ticket ids [`rules::tick002`] checks.

pub mod branch;
mod brief;
pub mod config;
pub mod doc;
pub mod doctor;
pub mod error;
pub mod event;
pub mod fold;
pub mod guards;
pub mod id;
pub mod index;
pub mod layout;
pub mod ledger;
pub mod links;
pub mod merge;
pub mod migrate;
pub mod model;
pub mod objects;
pub mod ops;
pub mod privacy;
pub mod redact;
pub mod rules;
pub mod schema;
pub mod scrub;
pub mod triage;

pub use error::{Candidate, LedgerError, Result};
pub use id::{EventId, TicketId};
pub use layout::Layout;
pub use ledger::{Applied, Ledger, LedgerConfig, RefMode};
