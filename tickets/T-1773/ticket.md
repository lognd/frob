---
id: T-1773
title: 'TestKnownGateRuleIds: SYS108 missing from _KNOWN_GATE_RULES (T-1624 landed
  without registering it)'
state: queued
kind: bug
origin: human
created: '2026-08-07'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
tests/test_gates.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known fails on a clean main checkout: generated_gate_rule_ids() reports SYS108 (src/frob/strata/_selfconform.py:1421, constructed by T-1624's land) but it is absent from _KNOWN_GATE_RULES in src/frob/gates/_waive.py. Confirmed via git log that SYS108 was introduced by 70879571 fix(tickets): land T-1624 -- pre-existing drift, not caused by T-1763. Add SYS108 to _KNOWN_GATE_RULES.