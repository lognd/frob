+++
id = "01M7EXTDQ20YDJ5323EA5394QY"
title = "crunk check: list unimplemented families in not_run at T1/T3"
type = "task"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-15T06:20:24Z"
updated = "2026-11-15T06:20:24Z"
idempotency_key = "crunkplan-fd8e30410167"
labels = ["no-story"]

[[acceptance]]
text = "a family with zero rules appears in not_run (test)"
bound = false
+++

Source: /home/logan/projects/frob-audit2-crunk.md, finding M4.
Evidence: not_run is empty because families with zero rules never register
Remedy: list families with no rules as not run, or add placeholder rules
Crates/files: crates/crunk-check, crates/gob-check
Verify against HEAD first; the audit ran on a stale binary.
