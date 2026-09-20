---
id: T-4990
title: Add 4 missing rule ids to _KNOWN_GATE_RULES registry
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: medium
blocked_by:
- T-4212
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: test_every_emitted_rule_literal_is_known passes
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
CI run 35476139324 on dev: tests/gates_suite/test_sys.py TestKnownGateRuleIds test_every_emitted_rule_literal_is_known fails because 4 rule ids constructed in src/frob/gates are missing from _KNOWN_GATE_RULES: GUARD001 (src/frob/gates/_guard_closure.py line 263), INV010 (src/frob/gates/_inv.py line 725), CLAIM001 (src/frob/gates/_claim_lint.py line 139), COV010 (src/frob/gates/_coverage.py line 1472). Paste all 4 into the frozenset inside the known-gate-rules zone in _waive.py. Distinct from T-4387 (done, DOC014) -- same class of bug, different rule ids, recurring gap.