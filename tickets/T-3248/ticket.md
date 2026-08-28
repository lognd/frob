---
id: T-3248
title: Migrate docstring archaeology into cited tickets (DOCARCH001 findings)
state: queued
kind: docs
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/**/*.py
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
T-2988 built DOCARCH001 (frob.gates._docstring_archaeology), which measures 418 repo-wide findings today: public docstrings that cite a ticket AND read as change-narrative rather than utility. T-2988 itself only built the detector and the standard (docs/modules/docstrings.md) per its acceptance criteria -- migrating the narrative INTO each cited ticket's body is separate, larger work, explicitly deferred by T-2988's own MIGRATION HAZARD note.

Before any batch migration: prove the archived-ticket write path is safe on ONE ticket first. T-2988's ticket body records the precedent incident -- 'frob ticket body' on a DONE ticket has previously written to the ACTIVE path and produced a DuplicateId that downed every ledger load repo-wide (see memory: archived-ticket-body-write-corrupts-main.md). Verify 'uv run frob ticket list' exits 0 after the first single-ticket write before scaling up.

MOVE, NEVER DELETE -- every migrated docstring keeps a one-line ticket reference in place of the narrative; do not mass-strip to hit a number. Re-run docarch001_violations after each batch and report the before/after count.