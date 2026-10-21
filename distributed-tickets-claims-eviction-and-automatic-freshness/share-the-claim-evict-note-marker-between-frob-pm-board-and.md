+++
id = "01M5E19XVSQ8D454Y9E6BJAWPM"
title = "Share the claim-evict note marker between frob-pm board and frob-worktree"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T01:30:40Z"
updated = "2026-10-21T01:30:40Z"
+++

board.rs EVICT_MARKER duplicates claim_evict.rs NOTE_MARKER (claim_evict.rs was leased elsewhere during ~WASSQCF). Extract one constant into a crate both depend on (frob-ledger) and use it in both.
