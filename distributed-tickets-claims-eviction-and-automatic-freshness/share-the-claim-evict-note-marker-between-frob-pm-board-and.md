+++
id = "01M5E19XVSQ8D454Y9E6BJAWPM"
title = "Share the claim-evict note marker between frob-pm board and frob-worktree"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T01:30:40Z"
updated = "2026-10-21T02:22:45Z"
scope = ["crates/frob-ledger/src/claim_window.rs", "crates/frob-pm/src/board.rs", "crates/frob-worktree/src/claim_evict.rs", "crates/frob-worktree/src/next.rs", "changelog.d/01M5E19XVSQ8D454Y9E6BJAWPM.changed.md"]
+++

board.rs EVICT_MARKER duplicates claim_evict.rs NOTE_MARKER (claim_evict.rs was leased elsewhere during ~WASSQCF). Extract one constant into a crate both depend on (frob-ledger) and use it in both.
