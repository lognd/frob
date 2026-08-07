---
id: T-0635
title: wire flake-quarantine stability tracking into frob test CLI run path
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0575
tier: ticket
sprint: null
scope:
- src/frob/app/test_runner.py
- src/frob/testing/**
- tests/test_app.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_app.py
  reason: 'T-0635''s scope covers src/frob/app/test_runner.py + src/frob/testing/**
    but

    omits the test file that already covers test_runner.py (tests/test_app.py,

    TestWaitCoverage class) -- the new _track_python_stability_and_gate wiring

    this ticket adds needs a frob:tests edge (TEST001 is an ERROR gate) and its

    own coverage, and the natural home for that is the same file that already

    tests this module''s other CLI dispatch paths. Adding tests/test_app.py so

    the ticket''s own tests can live where its sibling tests already do, rather

    than silently touching an out-of-scope file or inventing a second test file

    for one module.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_app.py::TestStabilityGate::test_quarantined_failure_promotes_to_ok
- tests/test_app.py::TestStabilityGate::test_hard_regressed_quarantine_stays_failed
- tests/test_app.py::TestStabilityGate::test_other_language_failure_not_masked
- tests/test_app.py::TestStabilityGate::test_all_sentinel_selection_is_noop
- tests/test_app.py::TestStabilityGate::test_empty_python_selection_is_noop
- tests/test_app.py::TestStabilityGate::test_capture_error_skips_gate
designated_repro_test: null
acceptance:
- text: GIVEN a flaky test with an open quarantine ticket WHEN frob test runs via
    the CLI THEN the run records history, the quarantined failure does not fail the
    build, and alarms surface for closed-ticket quarantines
  evidence:
  - tests/test_app.py::TestStabilityGate::test_quarantined_failure_promotes_to_ok
  - tests/test_app.py::TestStabilityGate::test_hard_regressed_quarantine_stays_failed
  - tests/test_app.py::TestStabilityGate::test_other_language_failure_not_masked
threat: null
component: null
---
T-0575 landed frob.testing._stability (record_outcomes, evaluate_gate, quarantine, alarms) but nothing in the frob test CLI path calls it -- tracking only happens if invoked programmatically. Wire capture/track + evaluate_gate + alarm surfacing into src/frob/app/test_runner.py so every frob test run updates history and applies quarantine semantics automatically. Disclosed cut in T-0575's Done report.