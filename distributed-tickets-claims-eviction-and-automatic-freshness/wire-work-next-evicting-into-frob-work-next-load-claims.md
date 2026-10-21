+++
id = "01M5DWZYEFXGXNRQ4KH8DKB004"
title = "Wire work_next_evicting into frob work --next (load claims tables, EvictPolicy, export types); holds/pauses and flap guard inputs"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T00:15:18Z"
updated = "2026-10-21T00:15:23Z"
+++

Follow-up of GSJJYF3. work_next_evicting exists in frob-worktree next.rs but verbs.rs does not call it. Load claims tables via gob_config::load, build ClaimWindows::from_tables and EvictPolicy (UTC offset, in_ci from CI env). Also feed held_or_paused and since_reclaim_secs; agent kind only known from local leases (note). Record ledger lease evict op (see 1N3HRWA).
