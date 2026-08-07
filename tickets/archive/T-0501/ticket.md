---
id: T-0501
title: 'strata audit G2/G7: vacuous NoFlow discharge when foreign->sink flow is un-modeled
  or no foreign-trust node exists'
state: done
kind: security
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_threat.py
- src/frob/strata/_claims.py
- tests/unit/strata/test_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: T-0501's litmus/regression tests for the G2/G7 flow-completeness fix live
    here
  actor: logan
  at: '2026-07-22'
evidence:
- tests/unit/strata/test_threat.py::TestFlowCompletenessGap::test_foreign_node_present_but_no_flow_to_sink_fails_closed
- tests/unit/strata/test_threat.py::TestFlowCompletenessGap::test_foreign_node_present_and_connected_elsewhere_still_fails_closed
- tests/unit/strata/test_threat.py::TestFlowCompletenessGap::test_no_foreign_node_anywhere_still_discharges_by_absence
- tests/unit/strata/test_threat.py::TestDischargeChokepointShape::test_noflow_from_a_specific_foreign_trust_node_discharges
designated_repro_test: null
threat: null
component: null
---
docs/audits/strata.md G2+G7 (HIGH/MEDIUM), from T-0401. _mitigation_is_chokepoint's first branch (_threat.py:1196) returns True when NoFlow holds with EVERY boundary removed -- i.e. the sink is simply unreachable from foreign in the model, so an incomplete/attacker-authored .strata discharges a real capability with NO mitigation modeled at all (G2). Same root cause as G7: _discharges_as_chokepoint's src=foreign expansion (_claims.py _expand) yields an empty source set when the model declares no foreign-trust node at all, so NoFlow proves vacuously (nothing to walk from) and every obligation on that model discharges with no adversary present. Fix direction: require at least one modeled path from a foreign source to the firing node (and at least one foreign-trust node in the model) before accepting the vacuous short-circuit as a discharge; otherwise emit a distinct 'obligation fires but sink unreachable / no adversary modeled -- model likely incomplete' diagnostic instead of silent PROVED. High-risk core-engine change (this family has the highest REJECT rate in repo history) -- build the counterexample litmus FIRST, confirm it currently discharges vacuously, THEN harden.