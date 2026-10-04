//! Authenticated derived-executable state outside the work tree (security.md 2.2, I4).
//!
//! Location decision: executable derived state (plans, compiled WASM, grammars)
//! lives in the per-user cache directory (`$XDG_CACHE_HOME/<product>/state`),
//! NOT under the git common dir where the check cache lives (~TSK0M4Y). The git
//! common dir is shared by every worktree and writable by any tool stage that
//! runs in a checkout, so a planted entry there is within the repository's
//! reach; the per-user directory is owner-only (0700) and sits beside the
//! per-machine key's trust boundary. Decision-bearing caches stay per
//! repository and are MAC'd by their own crate.
//!
//! The MAC key is the [`MachineKey`](crate::MachineKey) in the per-user config
//! directory (never the repository, never the cache directory, mode 0600).
//! Tool stages and packs run sandboxed with no filesystem grant on either
//! directory; the host process alone holds the key. On Windows the key file
//! and cache sit under the per-user `%APPDATA%`/`%LOCALAPPDATA%`, whose default
//! ACL admits only the owner, SYSTEM and administrators; as in `key`, no
//! explicit ACL is set because this crate forbids `unsafe`.

mod path;
mod store;

pub use path::{cache_dir, ci_active, resolve_cache_dir};
pub use store::{Discard, Lookup, StateError, StateStore};
