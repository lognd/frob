---
id: T-1140
title: 'arch: split remaining ~13 gate families out of src/frob/gates/__init__.py
  (T-1115 residue after DEBT/DEPR)'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
- tests/test_tickets_collision.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_tickets_collision.py
  reason: 'The TICK00x family move relocated tickets_gate/_tick* helpers into

    gates/_tickets_gate.py, which changed the frob:tests symref

    tests/test_tickets_collision.py''s TestTick002GateUnwaivable tests bind

    to (DRIFT002: src/frob/gates/__init__.py::tickets_gate no longer

    resolves). Fixing that stale symref requires touching this test file''s

    directives, so it needs to be in scope alongside tests/test_gates.py.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates_tick005.py::TestTick005MergeStateRegression::test_hand_resolved_conflict_resurrecting_done_ticket_is_flagged
- tests/test_gates_tickets_hygiene.py::TestTick003StaleArchive::test_above_default_error_threshold_errors
- tests/test_gates_tick009_tick010.py::TestTick009ScopeBreadthNudges::test_precisely_scoped_ticket_is_clean
- tests/test_tickets_priority.py::TestTick004QueueRot::test_stale_critical_ticket_flags
- tests/test_tickets_collision.py::TestTick002GateUnwaivable::test_draft_id_on_default_branch_is_a_violation
designated_repro_test: null
threat: null
component: null
---
T-1115 extracted one cohesive family (DEBT00x/DEPR00x, T-0412/T-0576) out
of src/frob/gates/__init__.py into gates/_debt_deprecated.py, following
T-1072/T-1077's one-family-per-land discipline
(gates/__init__.py: 9823 -> 9156 lines).

The remaining families named in T-1115's original acceptance criterion
still need extraction, one cohesive family per land, following the exact
same discipline (verbatim moves with directives intact, lazy call-time
imports back to frob.gates where init-time circularity threatens,
re-export only externally-called names verified by repo-wide grep,
split-carried INV006 waivers where prose with exclusivity vocabulary
moves, PII012 allowlist entries follow moved code):

SCOPE/PREWORK, INV00x, TEST00x, DECISIONS, TICK00x, COMPLIANCE00x,
SYS00x/DOC00x, DUP00x, REL00x, FUZZ00x, DOCLINK/DOCANCHOR, PERF,
run_gates spine, COV00x.

Acceptance: gates/__init__.py drops below the 800-line large-file
threshold with no public API change and all existing tests pass.