+++
id = "01M5E1MXHT9FNMKTH8EAYDK1H2"
title = "Wire ClaimRecord into next.rs and claim_evict.rs (held_or_paused, since_reclaim_secs)"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T01:36:40Z"
updated = "2026-10-21T01:50:12Z"
scope = ["crates/frob-worktree/src/next.rs", "crates/frob-worktree/src/claim_evict.rs"]
+++

Follow-up of XG6E8X3: use Workspace::claim_record; record reclaim on holder re-push. Wait for 51DGJH0.
