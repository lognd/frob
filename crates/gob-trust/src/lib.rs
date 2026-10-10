//! Per-machine key and MAC primitives shared by frob, grimble and crunk
//! (security.md 2.2 and 2.3).
//!
//! A [`MachineKey`] is 32 random bytes in `$XDG_CONFIG_HOME/gob/machine.key`,
//! created on first use with owner-only permissions. [`mac`] computes a
//! domain-separated keyed-blake3 [`Tag`]; [`verify`] checks one in constant
//! time. Nothing here logs, prints or `Debug`-formats key bytes.
//!
//! Windows: the file is written under the per-user `%APPDATA%` directory,
//! whose default ACL is already owner-plus-administrators. This crate forbids
//! `unsafe`, so it does not set an explicit owner-only ACL; that gap is
//! deliberate and documented, and no permission check runs there.
//!
//! ```
//! use gob_trust::{MachineKey, mac, verify};
//! let key = MachineKey::from_bytes([7; 32]);
//! let tag = mac(&key, "gob-cache-row/v1", b"row");
//! assert!(verify(&key, "gob-cache-row/v1", b"row", &tag).is_ok());
//! assert!(verify(&key, "gob-cache-row/v1", b"rox", &tag).is_err());
//! ```

mod error;
// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
mod guard;
mod key;
mod mac;
mod state;

pub use error::TrustError;
// frob:ticket 01M3ZX7TR7HMSXPCQSHFSG8SMS
pub use guard::{GuardError, STATE_DIRS, check_state_untracked};
pub use key::{KEY_LEN, MachineKey, default_key_path, resolve_key_path};
pub use mac::{Canonical, CanonicalWriter, Tag, mac, mac_record, verify, verify_record};
pub use state::{Discard, Lookup, StateError, StateStore, cache_dir, ci_active, resolve_cache_dir};
