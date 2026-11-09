+++
id = "01M713HQC2TF14B5F316HMYVT3"
title = "Wire E-SYNC-STALE into work/land and feed real diverged/conflict signals"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T21:31:09Z"
updated = "2026-11-09T23:03:02Z"
scope = ["crates/frob-worktree/src/verbs.rs", "crates/frob-land/src/verb.rs", "crates/frob-ledger/src/freshness.rs", "crates/frob-ledger/src/refresh.rs", "crates/frob-ledger/src/lib.rs", "crates/frob/src/freshness.rs", "crates/frob/src/lib.rs"]
+++

Found while working ~52CRMYV: only doable refuses E-SYNC-STALE; work and land do not depend on the freshness module, and view_freshness uses Signals::default().
