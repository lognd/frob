+++
id = "01M43JETBHW7FYNMR6SGVWFAEV"
title = "One shared atomic file write helper; migrate hand-rolled temp-and-rename copies"
type = "chore"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-04T13:43:05Z"
updated = "2026-10-04T13:43:05Z"

[[acceptance]]
text = "Given the workspace, when the inventory test runs, then every temp-and-rename write goes through the shared helper"
bound = false

[[acceptance]]
text = "Given a write killed mid-way, when the target is read, then it holds the old content whole"
bound = false
+++

~WS4WZBD added write_atomic (temp sibling, fsync, rename, keep permissions, cleanup on failure) in crates/gob-check/src/atomic.rs, but several crates hand-roll the same thing (at least the lease store, release bump and grimble ack). Extract one shared helper into the gob layer (an existing gob-* crate that owns filesystem primitives if one fits, else a small new one; check with frob search first), migrate every hand-rolled copy to it, and add a lint or test inventory that fails when a new hand-rolled temp-and-rename appears. Also fsync the parent directory after rename on Unix.
