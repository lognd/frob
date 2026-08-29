---
id: T-3384
title: fix gate:DOC, gate:DRIFT, gate:SELFAUDIT residue (EO slice)
state: in-progress
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/check_runner.py
- src/frob/tickets/_leases.py
- docs/commands/check.md
- src/frob/app/ticket_runner/_land_cmd.py
- tests/test_check_runner.py
- docs/modules/tickets-landing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/tickets.md
  reason: T-3358 holds a live lease on tickets.md; DOC011 finding at tickets.md:99
    deferred until that clears
  actor: logan
  at: '2026-08-29'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: DOC002 fix in _leases.py retargets an anchor in this doc
  actor: logan
  at: '2026-08-29'
body_changes:
- mode: append
  reason: BUG002 requires this for a pure doc/comment-directive correction with no
    runtime behavior change
  actor: logan
  at: '2026-08-29'
  old_length: 156
  new_length: 264
evidence:
- tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_none_progress_returns_none
- tests/unit/test_app_runners_batch6.py::TestTaskProgressCallback::test_updates_progress_with_language_qualified_label
- tests/test_ticket_leases.py::TestCommitTicketLedgerChange::test_rollback_on_land_in_progress_leaves_root_clean
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Series EO slice of self-gate zero drive: gate:DOC (5), gate:DRIFT (3), gate:SELFAUDIT (5). See T-3346/T-3343 for adjacent EM-owned gates (not touched here).

frob:no-behavior-change reason="doc-anchor/frob:tests-separator correction only, no code behavior changed"