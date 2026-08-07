---
id: T-0636
title: 'flake quarantine: hard regression under live quarantine is invisible to both
  gate and alarm'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: high
parent: T-0575
tier: ticket
sprint: null
scope:
- src/frob/testing/_stability.py
- tests/unit/testing/test_stability.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/testing.md
  reason: ticket's acceptance criteria explicitly requires updating docs/modules/testing.md's
    semantics section in the same change
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/testing/test_stability.py::TestHardRegression::test_past_thresh
- tests/unit/testing/test_stability.py::TestHardRegression::test_under_thresh
- tests/unit/testing/test_stability.py::TestHardRegression::test_mixed
- tests/unit/testing/test_stability.py::TestAlarms::test_hard_alarm
- tests/unit/testing/test_stability.py::TestAlarms::test_hard_no_alarm_flaky
- tests/unit/testing/test_stability.py::TestGate::test_hard_regress_fails
designated_repro_test: null
acceptance:
- text: GIVEN a quarantined test whose last N runs are all failures WHEN quarantine_alarms
    or evaluate_gate runs THEN the condition is surfaced as a hard-regression alarm
    and does not silently stay green
  evidence: []
threat: null
component: null
---
T-0575 reviewer MAJOR finding: evaluate_gate promotes on quarantine status alone (never re-checks is_flaky), and quarantine_alarms skips entries where is_flaky is false. A quarantined test that regresses to permanently-failing (all-F history) is by definition no longer flaky, so the gate keeps promoting it green forever AND the alarm never fires -- a silent skip-list, exactly what the ticket's mandate forbids. Fix: alarm (or gate-fail) when a quarantined test's recent history is all-fail beyond a threshold, distinct from the flaky case.