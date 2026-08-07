---
id: T-0833
title: 'compliance registry: flip 17 CMPL dispositions to handled_by:COMPLIANCE005,
  document gate in gates.md (T-0788 follow-up)'
state: done
kind: docs
origin: human
created: '2026-07-23'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/compliance.yaml
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestComplianceGate::test_compliance005_silent_on_handled_by_and_out_of_scope
- cmd:sh /tmp/claude-1000/-home-logan-projects-frob/28006941-9d5c-4153-b3fb-399b3b532639/scratchpad/t0833-evidence.sh
  exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
T-0788 wired COMPLIANCE005 live (compliance_gate dispatches
check_cmpl_registry in gates-fast) but left two disclosed gaps:

1. docs/design/registry/compliance.yaml: the 17 CMPL_REGISTRY_UNIT_IDS
   entries still carry T-0607's out_of_scope dispositions (each citing
   COMPLIANCE005 only in reason prose). T-0788's Description said "flip
   the 17 dispositions to handled_by:COMPLIANCE005"; its acceptance
   criterion only required that handled_by:COMPLIANCE005 be ACCEPTED
   (proven by test). Finish the intent: flip all 17 to
   handled_by:COMPLIANCE005 and confirm REG002 + COMPLIANCE005 stay
   green (the acceptance test already proves both dispositions pass).

2. docs/modules/gates.md: no COMPLIANCE005 row/section documents the new
   compliance gate (gates.md was outside T-0788's scope). Add the rule
   row + a short detail section following the TICK007 precedent.