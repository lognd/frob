+++
id = "01M7EXTYSR2H8GJDRW2FQDF1R7"
title = "crunk parity: compare Python rule-id multiset per E2E step"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-11-15T06:20:42Z"
updated = "2026-11-15T06:20:42Z"
idempotency_key = "crunkplan-805725fe5534"
labels = ["no-story"]

[[acceptance]]
text = "firing the wrong rule at a step fails the replay"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding M3.
Evidence: e2e_04 passes if any rule exits 1
Remedy: record Python check --json rule ids per step and compare without messages
Crates/files: crates/crunk/tests/e2e/replay.rs, tests/crunk-parity
Verify against HEAD first; the audit ran on a stale binary.
