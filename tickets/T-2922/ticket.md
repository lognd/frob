---
id: T-2922
title: 'Unwire the live may= auto-WIDENING Tier-A fixer: capability escalation is
  silently rubber-stamped today'
state: done
kind: security
origin: human
created: '2026-08-25'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_sync.py
- src/frob/gates/_fix_engine.py
- tests/test_gates.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine_sync.py
  reason: the two live widening call sites and their dispatch-table entries
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_gates.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_gates.py
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: unwiring SYS100 auto-widening touches its TIER_A_HANDLERS dispatch entry,
    its own tests, and the doc block describing the deleted fixers
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved
- tests/test_gates.py::TestFixEngineTierA::test_sys100_extended_violation_still_fires_and_is_not_auto_resolved
- tests/test_gates.py::TestFixEngineTierABatch2::test_tier_a_handlers_dict_covers_every_batch_rule
designated_repro_test: tests/test_gates.py::TestFixEngineTierA::test_sys100_core_violation_still_fires_and_is_not_auto_resolved
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
