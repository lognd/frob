---
id: T-2619
title: unlanded_branch_work anomaly class undocumented (T-2612 lease-premise audit)
state: done
kind: docs
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/modules/tickets.md
- docs/modules/tickets-lifecycle.md
- src/frob/tickets/_reconcile.py
evidence_scope:
- tests/test_ticket_reconcile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_reconcile.py
  reason: T-2619 removes both AFFECT001 waivers here once the doc gap they cite is
    closed, per the ticket's own instruction
  actor: logan
  at: '2026-08-19'
evidence:
- tests/test_ticket_reconcile.py::TestReconcileUnlandedBranchWork::test_reports_the_confirmed_leak_shape
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
src/frob/tickets/_reconcile.py::ReconcileReport and ::reconcile both carry
AFFECT001 waivers whose reason cited T-1720's "LIVE cross-worktree lease"
on docs/modules/tickets.md as the blocker preventing T-1934's fourth
anomaly class (unlanded_branch_work) from being documented there.

T-1720 is done. The premise has expired -- but the underlying doc gap is
real and still open: docs/modules/tickets.md has no mention of
unlanded_branch_work anywhere (grep confirms zero hits), so the "remove
this waiver and add a real doc section once T-1720 lands" instruction the
waiver reason itself promised was never carried out.

Add a docs/modules/tickets.md section (or extend the existing reconcile
section, docs/modules/tickets-lifecycle.md#frob-ticket-reconcile-t-0476)
describing the unlanded_branch_work anomaly class T-1934 added --
ReconcileReport's new field plus reconcile()'s detection of it -- then
remove both AFFECT001 waivers in src/frob/tickets/_reconcile.py.

Filed by T-2612's lease-premise audit (waiver-removal-vs-owed-work split).