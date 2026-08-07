---
id: T-0365
title: 'gates: investigate and disposition residual TEST006 (2) + TEST009 (2)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: null
threat: null
component: null
---
T-0204 family 7: 2 residual TEST006 findings + 2 residual TEST009 findings. Investigate root cause for each and disposition: fix, or reasoned frob:waive if the finding is a gate false-positive. NO blanket waiver. Acceptance: 0 unwaived TEST006/TEST009 findings; each disposition documented with reasoning; honest summary line.