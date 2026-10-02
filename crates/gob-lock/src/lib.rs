//! The ack lock file shared by every product (D28): `frob.lock`,
//! `grimble.lock`.
//!
//! A [`LockFile`] maps a symref string to the [`LockEntry`] recorded when a
//! human acknowledged it: the three facet digests (hex), who and when, an
//! optional reason, and for documentation bindings the digest of each bound
//! doc section ([`LockTarget`]). The file is TOML, keys sorted, so two saves
//! of the same content are byte-identical and diffs stay small. This crate
//! knows nothing about git, symbols or products beyond [`file_name`]: callers
//! decide what to acknowledge and how to commit the bytes.
//!
//! ```
//! use gob_lock::{LockEntry, LockFile};
//! let mut lock = LockFile::default();
//! lock.entries.insert("a.rs::f".to_owned(), LockEntry::new("s", "b", "d", "me", "2026-10-02T00:00:00Z"));
//! let text = lock.to_toml().unwrap();
//! assert_eq!(LockFile::from_toml(&text).unwrap(), lock);
//! ```

mod diff;
mod file;

pub use diff::{Facet, LockDiff, diff};
pub use file::{LOCK_VERSION, LockEntry, LockError, LockFile, LockTarget, file_name};
