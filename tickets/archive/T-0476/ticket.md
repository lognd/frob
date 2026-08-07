---
id: T-0476
title: 'ticket<->worktree binding + liveness reconcile (regular op AND recovery):
  every in-progress ticket records its worktree path/branch; frob ticket reconcile
  heals the two anomaly classes without coordinator hand-work -- (1) in-progress ticket
  with no live worktree = dead/stalled agent (auto-requeue to queued + release lease,
  or flag), (2) live worktree with no in-progress ticket = orphan (auto-clean via
  tiered frob clean). Detect stalls structurally (no live worktree / no recent activity)
  instead of the coordinator polling output-file mtimes. Sharpens T-0456; relates
  T-0473 (worktree-local lease) T-0475 (splice state resurrection) T-0457 (tiered
  clean)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_reconcile.py
- src/frob/tickets/__init__.py
- src/frob/__main__.py
- docs/modules/tickets.md
- tests/test_ticket_reconcile.py
- tests/unit/test_app_runners_batch7.py
- tickets.md
- pyproject.toml
- .frob-release.json
- CHANGELOG.md
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: T-0476 lease-registry reuse reconcile impl
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/tickets/__init__.py
  reason: T-0476 lease-registry reuse reconcile impl
  actor: logan
  at: '2026-07-21'
- op: add
  glob: src/frob/__main__.py
  reason: T-0476 lease-registry reuse reconcile impl
  actor: logan
  at: '2026-07-21'
- op: add
  glob: docs/modules/tickets.md
  reason: T-0476 lease-registry reuse reconcile impl
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/test_ticket_reconcile.py
  reason: T-0476 lease-registry reuse reconcile impl
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_app_runners_batch7.py
  reason: T-0476 lease-registry reuse reconcile impl
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tickets.md
  reason: T-0476 lease-registry reuse reconcile impl
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: 'T-0476: REL001 minor bump for reconcile''s new public API'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: 'T-0476: REL001 minor bump for reconcile''s new public API'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: 'T-0476: REL001 minor bump for reconcile''s new public API'
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: 'T-0476: REL001 minor bump for reconcile''s new public API'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_dry_run_reports_but_does_not_requeue
- tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_apply_requeues_stale_hold_and_releases_lease
- tests/test_ticket_reconcile.py::TestReconcileStaleHold::test_live_in_progress_ticket_with_lease_is_untouched
- tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree::test_live_worktree_with_no_lease_is_flagged_not_removed
- tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree::test_apply_and_remove_orphans_actually_removes_it
- tests/test_ticket_reconcile.py::TestReconcileOrphanWorktree::test_worktree_holding_a_live_lease_is_not_orphan
- tests/unit/test_app_runners_batch7.py::TestTicketReconcileCli::test_no_anomalies_logs_clean_summary
- tests/unit/test_app_runners_batch7.py::TestTicketReconcileCli::test_load_error_exits_1
designated_repro_test: null
threat: null
component: null
---
