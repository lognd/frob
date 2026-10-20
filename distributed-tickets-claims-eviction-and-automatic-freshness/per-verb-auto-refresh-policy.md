+++
id = "01M5CW04GHM970H5KR4EV5KK0X"
title = "Per-verb auto-refresh policy"
type = "task"
category = "in-progress"
priority = "high"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-20T14:38:42Z"
updated = "2026-10-20T19:13:28Z"
idempotency_key = "dt-DT08"
scope = ["crates/frob-ledger/src/sync_policy.rs", "crates/frob-ledger/src/config.rs", "crates/frob-ledger/src/lib.rs", "crates/frob/src/ticket/mod.rs", "crates/frob/src/ticket/read.rs", "crates/frob/src/sync_hook.rs", "crates/frob/src/lib.rs", "docs/schemas/config.json", "docs/reference/config.md", "docs/design/distributed-tickets.md", "crates/frob-ledger/src/refresh.rs", "crates/frob/tests/it/sync_policy.rs", "crates/frob/tests/it/main.rs", "crates/frob-ledger/Cargo.toml", "crates/frob/src/refresh_cmd.rs"]

[[links]]
kind = "blocked-by"
target = "01M5CW049SPSRGGP5ENQD7BPB3"

[[links]]
kind = "blocked-by"
target = "01M5CW04D5QJCJ5S72V8PE22M6"

[[acceptance]]
text = "Reads kick a detached background refresh at most once per ttl and CI disables it"
bound = true

[[acceptance]]
text = "doable probes in the foreground within the budget and appends a W-SYNC notice"
bound = true
+++

Background kick for reads (never network inline), foreground 3s budget for work, doable and land, stale_error 24h refusal for mutating verbs, off in CI. See docs/design/distributed-tickets.md.
