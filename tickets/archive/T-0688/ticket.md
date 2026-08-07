---
id: T-0688
title: exhaustive-exception gate + errors-as-values advisory over may-raise sets
state: done
kind: feature
origin: human
created: '2026-07-22'
priority: medium
blocked_by:
- T-0686
parent: T-0685
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/arch/**
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/arch/**
  reason: the advisory half lives beside the T-0332 recommender in arch
  actor: logan
  at: '2026-07-22'
- op: add
  glob: src/frob/check/__init__.py
  reason: T-0688's new exhaustive_handling gate must be registered in check/_STAGE_GROUPS'
    gates-native group so it stays --only reachable, and to satisfy the existing gate/stage-coverage
    drift-lock test (tests/system/test_cli_check.py::TestCheckStageGroups::test_available_stages_cover_every_gate_and_tool)
    -- a mechanical one-line registration required by this ticket's own gate wiring,
    not a new feature
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_gates.py::TestExhaustiveHandlingGate::test_partial_catch_of_named_type_fires_exhaust002
- tests/test_gates.py::TestExhaustiveHandlingGate::test_unknown_without_catch_all_fires_exhaust001
- tests/test_gates.py::TestExhaustiveHandlingGate::test_catch_all_of_unknown_does_not_fire_exhaust001
- tests/test_gates.py::TestExhaustiveHandlingGate::test_declared_frob_raises_directive_discharges_exhaust002
- tests/test_gates.py::TestExhaustiveHandlingGate::test_function_with_no_catches_is_not_a_boundary
- tests/test_gates.py::TestErrorsAsValuesAdvisory::test_public_raiser_with_no_handling_caller_recommends_result
- tests/test_gates.py::TestErrorsAsValuesAdvisory::test_public_raiser_with_handling_caller_not_flagged
- tests/test_gates.py::TestErrorsAsValuesAdvisory::test_private_raiser_not_flagged
- tests/test_gates.py::TestErrorsAsValuesAdvisory::test_only_ubiquitous_or_unknown_raises_not_flagged
designated_repro_test: null
acceptance:
- text: GIVEN a boundary catching a strict subset of its guarded may-raise set WHEN
    the gate runs THEN the missing exception types are named; GIVEN a public raiser
    with unhandling callers WHEN arch advisories run THEN a Result recommendation
    fires with the raise sites
  evidence:
  - tests/test_gates.py::TestExhaustiveHandlingGate::test_partial_catch_of_named_type_fires_exhaust002
  - tests/test_gates.py::TestErrorsAsValuesAdvisory::test_public_raiser_with_no_handling_caller_recommends_result
threat: null
component: null
---
Child 3 of T-0685 (blocked by the python resolver landing; extend to C++ when its child lands). Two consumers of the may-raise sets: (1) EXHAUSTIVE-HANDLING gate: a try block or declared boundary function is exhaustive iff every member of the guarded may-raise set is caught, explicitly declared-propagated (a frob: directive), or waived with reason; Unknown in the set forces a catch-all or fixing the unresolvable call -- silent non-exhaustiveness impossible. (2) ERRORS-AS-VALUES advisory (suggestion severity, T-0332 noise discipline): a public function with non-empty recoverable may-raise whose callers do not handle it recommends typani Result[T,E], with the raise-site list as the sketch; exceptions remain sanctioned for programmer bugs (assert/invariant class exempt). Wire into T-0623's fallibility family; register rule ids in _KNOWN_GATE_RULES; docs in the same change.