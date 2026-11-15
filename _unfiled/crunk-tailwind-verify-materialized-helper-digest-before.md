+++
id = "01M7EXV2H4KC53Q9FYCYMSSMA3"
title = "crunk-tailwind: verify materialized helper digest before running"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:45Z"
updated = "2026-11-15T06:20:45Z"
idempotency_key = "crunkplan-f8b943d17fc3"
labels = ["no-story"]

[[acceptance]]
text = "a tampered helper with the expected name is rewritten or rejected (test)"
bound = false
+++

Source: ~/projects/frob-audit-grimble-crunk.md, finding L12.
Evidence: existing helper-<hash>.mjs is trusted by name
Remedy: verify digest on reuse or rewrite atomically
Crates/files: crates/crunk-tailwind/src/runtime/exec.rs:105-113
Verify against HEAD first; the audit ran on a stale binary.
