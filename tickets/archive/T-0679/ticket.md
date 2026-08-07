---
id: T-0679
title: 'flake quarantine: recent-tail-window variant of is_hard_regression'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
blocked_by:
- T-0636
parent: T-0575
tier: ticket
sprint: null
scope:
- src/frob/testing/_stability.py
- tests/unit/testing/test_stability.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/testing/test_stability.py::TestHardRegression::test_tail_stale
- tests/unit/testing/test_stability.py::TestHardRegression::test_tail_short
- tests/unit/testing/test_stability.py::TestHardRegression::test_tail_cfg
- tests/unit/testing/test_stability.py::TestAlarms::test_hard_alarm_tail
- tests/unit/testing/test_stability.py::TestGate::test_hard_regress_tail_fails
designated_repro_test: null
acceptance:
- text: GIVEN history [P] followed by K consecutive fails under live quarantine WHEN
    evaluate_gate and hard_regression_alarms run THEN the gate stays red and the alarm
    fires
  evidence:
  - tests/unit/testing/test_stability.py::TestAlarms::test_hard_alarm_tail
  - tests/unit/testing/test_stability.py::TestGate::test_hard_regress_tail_fails
threat: null
component: null
---
T-0636's is_hard_regression checks all-fail over the ENTIRE bounded 20-run window, so a single stale pass anywhere in the window defeats detection for up to 19 subsequent all-fail runs -- a real hard regression stays promoted and un-alarmed that whole time. Add a recent-tail rule (last K runs all-fail, K configurable, default ~5) alongside or replacing the whole-window rule, with tests covering the one-old-pass-then-long-fail-tail case T-0636's reviewer identified. Update docs/modules/testing.md semantics. NOTE: the hard-regression CLI/alarm wiring is T-0635's scope; T-0636's a lost draft (its scope is covered by T-0635) duplicated it and needs no refile.