---
id: T-4607
title: post-land sweep raises quarantine on its own lease-file/doc noise (TICK010
  on .git/frob-leases, DOC012 docs/commands) and dirties the root ratchet lock, forcing
  every land synchronous
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- src/frob/tickets/_land.py
- tests/unit/rapid_sweep_suite/*
- src/frob/gates/_fix_engine_sync.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/app/ticket_runner/_rapid_sweep.py
  reason: quarantine raise filtering, root-write fix
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: possible root ratchet-lock writer
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/tickets/_land.py
  reason: land staging writer for ratchet lock
  actor: logan
  at: '2026-09-19'
- op: add
  glob: tests/unit/rapid_sweep_suite/*
  reason: positive-control tests for filtering
  actor: logan
  at: '2026-09-19'
- op: add
  glob: docs/**
  reason: why-file / doc updates
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: docs/**
  reason: too broad, narrowing
  actor: logan
  at: '2026-09-19'
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: second unguarded writer of capability-via-ratchet.lock.json
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: unused in final diff -- freeing for T-4599
  actor: logan
  at: '2026-09-19'
body_changes:
- mode: append
  reason: 'T-4709: preserve caller-name detail trimmed from _fix_engine_sync.py'
  actor: logan
  at: '2026-09-19'
  old_length: 0
  new_length: 432
evidence:
- tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities::test_drops_git_metadata_path_such_as_a_lease_file
- tests/unit/rapid_sweep_suite/test_dispose.py::TestNormalizeIdentities::test_leaves_a_real_tickets_dir_finding_alone
- tests/unit/rapid_sweep_suite/test_filing.py::TestRaiseQuarantineForRedBatch::test_directory_shaped_finding_is_filed_but_not_quarantined
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_without_land_lock_reports_but_does_not_write
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_bumps_growth_this_lands_diff_caused
- tests/gates_suite/test_fix_engine.py::TestFixEngineTierA::test_sys111_ratchet_bump_still_applies_through_scope_lease_filter
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---

T-4709 follow-up (condensed from a comment in fix_sys111_capability_
ratchet_sync in src/frob/gates/_fix_engine_sync.py, trimmed for
DOCARCH002's 12-line cap): this handler's two current callers are
_land_cmd._sweep_apply_tier_a_pre_commit and
_sweep_apply_tier_a_and_commit. This is the exact T-4563 regression
shape, but for this module's OWN unconditional write rather than the
one T-4563 already gated in frob.strata._effects.