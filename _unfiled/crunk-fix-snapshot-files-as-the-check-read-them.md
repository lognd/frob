+++
id = "01M7EXTZERQ39XZDTR3FWRHKJN"
title = "crunk-fix: snapshot files as the check read them"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:42Z"
updated = "2026-11-15T06:20:42Z"
idempotency_key = "crunkplan-2f5512fc4121"
labels = ["no-story"]

[[acceptance]]
text = "a file edited between check and fix is refused (test)"
bound = false
+++

Source: /home/logan/projects/frob-audit-grimble-crunk.md, finding L1.
Evidence: snapshot read after the check, so edits in between apply at stale offsets
Remedy: snapshot from the check file bytes or compare digests
Crates/files: crates/crunk-fix/src/run.rs:36-59
Verify against HEAD first; the audit ran on a stale binary.
