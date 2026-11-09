+++
id = "01M713HQC2TF14B5F316HMYVT3"
title = "Wire E-SYNC-STALE into work/land and feed real diverged/conflict signals"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-09T21:31:09Z"
updated = "2026-11-09T23:19:48Z"
scope = ["crates/frob-worktree/src/verbs.rs", "crates/frob-land/src/verb.rs", "crates/frob-ledger/src/freshness.rs", "crates/frob-ledger/src/refresh.rs", "crates/frob-ledger/src/lib.rs", "crates/frob/src/freshness.rs", "crates/frob/src/lib.rs", "crates/frob/src/ticket/mod.rs", "crates/frob/tests/it/sync_policy.rs", "crates/frob-land/tests", "changelog.d"]
+++

Found while working ~52CRMYV: only doable refuses E-SYNC-STALE; work and land do not depend on the freshness module, and view_freshness uses Signals::default().
