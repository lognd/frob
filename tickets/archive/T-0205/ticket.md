---
id: T-0205
title: pytest collects Test*-prefixed product classes -- set __test__ = False
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_models.py
- src/frob/testing/_models.py
- src/frob/testing/_runners.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestSelect::test_direct_hit
- tests/test_gates.py::TestCoverageGate::test_waive002_honors_loaded_policy_rule_ids
designated_repro_test: null
threat: null
component: null
---
User report 2026-07-18 (CI warnings summary): PytestCollectionWarning for gates/_models.py::TestPolicy and testing/_runners.py::TestingError -- pytest matches the Test* class-name prefix and tries to collect product classes. Fix: annotated __test__: bool = False on TestPolicy, TestingError, and TestRunReport (testing/_models.py), matching the existing precedent on process/parsers/common.py::TestCase. Verified: pytest --collect-only over tests/test_gates.py + tests/test_testing.py emits zero PytestCollectionWarning; both suites still pass.