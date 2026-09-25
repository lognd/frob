---
id: T-6522
title: 'ticket reconcile stale-field detection regressed: always reports empty'
state: queued
kind: bug
origin: agent
created: '2026-09-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- tests/test_ticket_reconcile.py
- src/frob/tickets
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
Found while draining CI run 36173008509 (dev 473cee7656). Reproduces on
ubuntu-latest and macos-latest.

All 4 tests in tests/test_ticket_reconcile.py::TestReconcileStripStaleFields
fail with the same shape (assert {} == {'branch': '...stale-worktree'}):
- test_dry_run_reports_but_does_not_strip
- test_apply_strips_stale_fields
- test_second_run_is_a_no_op
- test_leased_ticket_is_skipped_not_written

The reconcile pass that strips stale worktree/branch fields from a ticket's
ledger entry appears to no longer detect (or no longer report) the stale
'branch' field at all -- every test gets an empty dict where a populated one
was expected. This looks like a real regression in the stale-field
detection path, not a test/fixture drift issue.

Proposed fix: bisect the reconcile stale-field detector against recent
commits touching ticket reconcile/ledger field stripping; the dry-run and
apply paths both regressed identically, suggesting a shared helper broke.
