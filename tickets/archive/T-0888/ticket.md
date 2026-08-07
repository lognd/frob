---
id: T-0888
title: register REG011 in _KNOWN_GATE_RULES + CHK-GATE-REG011 registry entry (T-0680
  follow-up)
state: dropped
kind: bug
origin: agent
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- docs/design/registry/check-coverage.yaml
- tests/test_check_coverage_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN frob check runs WHEN the registry gate summary renders THEN REG011 appears
    as a known rule and REG010 reports no missing CHK-GATE-REG011 registry entry
  evidence: []
threat: null
component: gates
---
Follow-up to T-0680 (landed 0d7e2f2b): REG011 (out_of_scope caught_by verification, WARN) is implemented in _registry_exhaustiveness.py but not registered in frob.gates.__init__._KNOWN_GATE_RULES nor in docs/design/registry/check-coverage.yaml (CHK-GATE-REG011 entry) -- deferred because another agent held gates/__init__.py during T-0680. Register both (REG010 will demand the yaml row). Refiled from a worktree draft that did not survive T-0680's ledger recovery.

## Drop reason
- 2026-07-23: absorbed by T-0903 (audit finding H3): REG011 is one of 7 missing _KNOWN_GATE_RULES ids being registered together, with T-0901 adding the drift-lock