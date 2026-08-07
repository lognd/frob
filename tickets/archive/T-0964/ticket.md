---
id: T-0964
title: T-0901 drift-lock is blind to rule ids referenced via module-level constants
  (REL_*/SYS_* false-negative)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
designated_repro_test: null
acceptance:
- text: given a rule id referenced only via a module-level constant and absent from
    _KNOWN_GATE_RULES, when the drift-lock test runs, then it fails naming that id
  evidence:
  - tests/test_gates.py::TestKnownGateRuleIds.test_every_emitted_rule_literal_is_known
  - tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
threat: null
component: null
---
Found during T-0961: the drift-lock test test_every_emitted_rule_literal_is_known scans only inline rule=string literals, so 30 real firing rule ids referenced as rule=<MODULE_CONSTANT> were invisible to it -- it passed while _KNOWN_GATE_RULES was missing them all. Extend the scan to also resolve module-level constant assignments (REL_*/SYS_*/any name whose value is a rule-id-shaped string that flows into a rule= kwarg), so constant-referenced ids are checked identically to literals. Prove with a before-fails case: temporarily removing a constant-referenced id from _KNOWN_GATE_RULES must fail the test.