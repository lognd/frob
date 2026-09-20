---
id: T-4623
title: 'Clean docstrings: test_tickets_velocity/triage_dates/parent/organization/etc,
  24 misc files (DOCARCH001)'
state: queued
kind: docs
origin: agent
created: '2026-09-19'
priority: medium
parent: T-4421
tier: ticket
sprint: v0.534.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates_fmt_directives.py
- tests/test_coverage.py
- tests/test_waive_gate.py
- tests/test_tickets_velocity.py
- tests/test_tickets_triage_dates.py
- tests/test_tickets_parent.py
- tests/test_tickets_organization.py
- tests/test_tickets_live_tracker.py
- tests/test_tickets_leases.py
- tests/test_tickets_lease.py
- tests/test_tickets_collision.py
- tests/test_tickets_cmd_evidence.py
- tests/test_ticket_store_stale_snapshot.py
- tests/test_ticket_reconcile.py
- tests/test_ticket_land_proof_claims.py
- tests/test_ticket_evidence.py
- tests/test_serve_daemon.py
- tests/test_scaffold_worktree_lease_hook.py
- tests/test_release.py
- tests/test_lang_support.py
- tests/test_excludes.py
- tests/test_evidence_integrity.py
- tests/test_cache_gate.py
- tests/test_arch_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: parent
  old_value: null
  new_value: T-4421
  reason: child of T-4421 docarch debloat split
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: null
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given a frob check scoped to these 24 files, when DOCARCH001 is measured,
    then the combined finding count is 0
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Child of T-4421 (debloat sprint v0.534.0). Measured 2026-09-19: DOCARCH001 finding count for these 24 files was 27 (2+2+23x1) on a truncated repo-wide check; re-measure per-file before starting, the run that produced this count did not finish and may be an undercount. tests/test_worktree_guard.py (1 finding) deliberately excluded -- leased by in-progress T-4546, file it separately or wait. Rewrite each flagged docstring to state WHAT the symbol/test does; move any narrative worth keeping into the ticket that made the change via 'frob ticket body <id> --append'. Do not touch files leased by another in-progress ticket.