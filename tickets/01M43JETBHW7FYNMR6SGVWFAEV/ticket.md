+++
id = "01M43JETBHW7FYNMR6SGVWFAEV"
title = "One shared atomic file write helper; migrate hand-rolled temp-and-rename copies"
type = "chore"
category = "in-progress"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T13:43:05Z"
updated = "2026-10-04T22:35:27Z"
scope = ["Cargo.lock", "crates/gob-fs/Cargo.toml", "crates/gob-fs/src", "crates/gob-fs/tests", "crates/gob-check/Cargo.toml", "crates/gob-check/src/atomic.rs", "crates/gob-check/src/fix.rs", "crates/gob-check/src/lib.rs", "crates/frob-evidence/Cargo.toml", "crates/frob-evidence/src/store.rs", "crates/frob-lease/Cargo.toml", "crates/frob-lease/src/store.rs", "crates/frob-release/Cargo.toml", "crates/frob-release/src/bump.rs", "crates/frob-release/src/lib.rs", "crates/frob-release/tests/changelog.rs", "crates/frob-worktree/Cargo.toml", "crates/frob-worktree/src/gc/stamp.rs", "crates/gob-lock/Cargo.toml", "crates/gob-lock/src/file.rs", "crates/gob-trust/Cargo.toml", "crates/gob-trust/src/state/store.rs", "crates/grimble/Cargo.toml", "crates/grimble/src/ack.rs", "crates/gob-fs/src/lib.rs", "crates/gob-fs/tests/inventory.rs"]

[[acceptance]]
text = "Given the workspace, when the inventory test runs, then every temp-and-rename write goes through the shared helper"
bound = true

[[acceptance]]
text = "Given a write killed mid-way, when the target is read, then it holds the old content whole"
bound = true
+++

~WS4WZBD added write_atomic (temp sibling, fsync, rename, keep permissions, cleanup on failure) in crates/gob-check/src/atomic.rs, but several crates hand-roll the same thing (at least the lease store, release bump and grimble ack). Extract one shared helper into the gob layer (an existing gob-* crate that owns filesystem primitives if one fits, else a small new one; check with frob search first), migrate every hand-rolled copy to it, and add a lint or test inventory that fails when a new hand-rolled temp-and-rename appears. Also fsync the parent directory after rename on Unix.
