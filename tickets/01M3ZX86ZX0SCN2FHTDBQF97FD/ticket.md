+++
id = "01M3ZX86ZX0SCN2FHTDBQF97FD"
title = "TICK009 misfiled-ticket with machine fix"
type = "task"
category = "in-progress"
priority = "high"
points = 2
parent = "01M3ZX776JJSRQXW8Q0327K9QN"
reporter = "lognd"
created = "2026-10-03T03:34:46Z"
updated = "2026-10-11T19:38:57Z"
idempotency_key = "m2-nav-tick007"
labels = ["milestone:2", "area:navigation", "creates:crates/frob-ledger/src/misfiled.rs", "creates:crates/frob/tests/ticket_misfiled.rs", "creates:crates/gob-mdtest/coverage-allowlist.toml"]
scope = ["crates/frob-obligations/src/tick_misfiled.rs", "crates/frob-ledger/src/misfiled.rs", "crates/frob/tests/ticket_misfiled.rs", "crates/gob-mdtest/coverage-allowlist.toml"]

[[links]]
kind = "blocked-by"
target = "01M3ZX85S7ASFGT31GDYMRB5JX"

[[acceptance]]
text = "Given all files at computed paths, when checked, then it does not fire"
bound = false

[[acceptance]]
text = "Given a ticket file at a stale path, when checked, then TICK009 fires and the fix is `frob ticket reindex`"
bound = false
+++

Implements navigation.md section 2.2.

On the tip of the branch every ticket file is at its computed path; the fix is frob ticket reindex.
