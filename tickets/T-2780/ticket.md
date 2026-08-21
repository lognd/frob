---
id: T-2780
title: add set-parent to tickets-lifecycle.md's verb-strategy table doc
state: queued
kind: docs
origin: human
created: '2026-08-21'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets-lifecycle.md
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
T-2770 added "set-parent" to LEDGER_VERB_STRATEGY
(src/frob/app/ticket_runner/_ledger_mirror.py) as GENERIC_COMMIT_MIRRORED,
which trips AFFECT001 (the table's affects()-closure doc,
docs/modules/tickets-lifecycle.md#one-verb-table-not-two-sets-t-2603,
was not touched in the same diff). docs/modules/tickets-lifecycle.md was
under a live cross-worktree lease (T-2557) at fix time and could not be
added to T-2770's own scope, so the finding is waived there instead
(frob:waive AFFECT001) pending this ticket. Add "set-parent" to the
verb enumeration/table at that doc anchor, then this ticket's waiver in
_ledger_mirror.py can be removed.
