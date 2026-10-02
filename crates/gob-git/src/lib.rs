//! In-process git for every goblin.
//!
//! Reads go through `gix` (pinned at 0.87.1; 0.88.0 does not resolve on
//! crates.io at the time of writing). The ledger write primitive
//! [`Repo::commit_paths`] builds a tree from a ref's tip plus the changed
//! paths (never from an index), writes a commit, and moves the ref by
//! compare-and-swap. Only three operations spawn `git`, through `gob-exec`
//! so the spawn counter sees them: `worktree add`, `merge`, `push`; see
//! [`SpawnClass`]. Design: `git-io.md` sections 1 to 3, decision D23.

mod error;
mod fallback;
mod ledger;
mod read;
mod relpath;
mod spawn;
mod status;

pub use error::GitError;
pub use fallback::MergeOutcome;
pub use ledger::{CommitOptions, CommitOutcome};
pub use read::{Head, Repo, WorktreeInfo};
pub use relpath::RelPath;
pub use spawn::SpawnClass;
pub use status::{ChangeKind, ChangedPath, StatusEntry, StatusKind, StatusOptions, TreeRef};

/// A git object id (SHA-1 today); re-exported from gix.
pub use gix::ObjectId as Oid;
