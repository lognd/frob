---
id: T-0603
title: wire derived-state integrity manifest into frob check/gates as a hard block
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0570
tier: ticket
sprint: null
scope:
- src/frob/check/**
- src/frob/gates/**
- tests/unit/test_check.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_check.py
  reason: 'Evidence for the new wiring (corrupt-vs-absent derived-state precheck)

    lives in tests/unit/test_check.py, alongside the existing _run_gates/

    run_check unit tests it extends; adding a test file for one new function

    would duplicate the existing suite''s fixtures and test-collection setup.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/gates.md
  reason: 'docs/modules/gates.md is where the rule-catalog frob:doc anchor for the

    new DERIVED001 precheck lives; documenting a new public symbol in the

    same change as the code is required by the playbook (section: New public

    symbols need both a frob:doc and a frob:tests edge).

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_corrupt_artifact_fails_closed_before_any_stage_runs
- tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_absent_artifact_is_not_a_violation
- tests/unit/test_check.py::TestCheckBuildsGraphOnce::test_run_check_calls_build_graph_exactly_once
designated_repro_test: null
acceptance:
- text: GIVEN a truncated .frob/cache.db WHEN frob check runs THEN the run fails closed
    naming the corrupt artifact before any gate consumes it
  evidence:
  - tests/unit/test_check.py::TestDerivedStateIntegrityGate::test_corrupt_artifact_fails_closed_before_any_stage_runs
threat: null
component: null
---
T-0570 landed the doctor-first fingerprint/format check (verify_derived_state in src/frob/doctor.py) but frob check/gates still consume derived state (.frob caches, coverage stamp, baseline) without consulting it -- corrupt state is reported by doctor, not blocked at the gate boundary. Wire verify_derived_state in so a corrupt derived artifact fails closed before any gate trusts it. NOTE: T-0570's Done report references this as T-draft-1327a057 (and mislabels it as T-0571); the draft did not survive land (T-0577 tracks the draft-loss bug), so this ticket is its real replacement.