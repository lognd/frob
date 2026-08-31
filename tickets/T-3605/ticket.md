---
id: T-3605
title: 'COV003: T-3410 cmd: evidence invalid for bug-kind ticket'
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3410/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
COV003: T-3410 (kind=bug, state=done) has evidence entry `cmd:pytest
tests/unit/test_scaffold_project.py tests/unit/test_scaffold_managed.py`.
The `cmd:` evidence channel (frob ticket evidence --evidence-cmd) is valid
only for docs/ux kind tickets; T-3410 is kind=bug so COV003 flags it.

FIX: replace the cmd: evidence entry with real pytest node ids that cover
the same claim (docs/index.md.j2 corrected to match README.md.j2 wording,
verified via the scaffold test suite), using
`uv run frob ticket evidence T-3410 --replace <old> <new> --reason ...`
(the ticket is state=done but not archived, so --replace without
--archived applies).

Rule id: COV003.
