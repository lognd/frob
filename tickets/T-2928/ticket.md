---
id: T-2928
title: 'WIRE001 and REF002 both MISS provably dead symbols: measured 1-of-3 detector
  hit rate on a controlled deletion'
state: done
kind: bug
origin: human
created: '2026-08-25'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_wire.py
- src/frob/gates/_refs.py
- tests/test_gates.py
- docs/modules/gates.md
- tests/test_refs_gate.py
- tests/unit/gates/test_refs.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_wire.py
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: src/frob/gates/_refs.py
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_gates.py
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: docs/modules/gates.md
  reason: investigate why WIRE001/REF002 both missed a controlled dead-symbol deletion
    (T-2900/T-2905); add regression fixtures and document detector scope
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/test_refs_gate.py
  reason: REF002 regression fixtures belong beside its existing test suite, not test_gates.py
  actor: logan
  at: '2026-08-25'
- op: add
  glob: tests/unit/gates/test_refs.py
  reason: REF002 regression fixtures belong beside its existing test suite, not test_gates.py
  actor: logan
  at: '2026-08-25'
evidence:
- tests/test_gates.py::TestWire001DiffScopingMissesPreExistingDeadSymbols::test_pre_existing_dead_symbol_untouched_by_this_diff_is_not_flagged
- tests/test_gates.py::TestWire001DiffScopingMissesPreExistingDeadSymbols::test_the_same_dead_symbol_newly_added_by_this_diff_is_flagged
- tests/unit/gates/test_refs.py::TestRef002FileGranularityMissesDeadSymbols::test_dead_private_symbol_in_a_well_referenced_file_is_not_flagged
- tests/unit/gates/test_refs.py::TestRef002FileGranularityMissesDeadSymbols::test_file_containing_only_the_dead_symbol_still_fires_ref001
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
