---
id: T-0498
title: 'strata audit G1: bind ENDORSE Boundary predicates to observed code (THREAT003
  discharge is a declared string, not a proof)'
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
- src/frob/strata/_selfconform.py
- src/frob/strata/_code_binding.py
- tests/test_vet_containment.py
- tests/unit/strata/test_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_vet_containment.py
  reason: test fixtures exercising the ENDORSE-boundary discharge semantics changed
    by the G1 fix must be updated alongside it
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: test fixtures exercising the ENDORSE-boundary discharge semantics changed
    by the G1 fix must be updated alongside it
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_no_evidence_ref_does_not_discharge_g1
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_dangling_obligation_does_not_discharge_g1
- tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_matching_predicate_discharges
- tests/test_vet_containment.py::TestBuildContainmentReport::test_contained_finding_when_obligation_discharged
designated_repro_test: null
threat: null
component: null
---
docs/audits/strata.md G1 (HIGH), from T-0401. _mitigation_is_chokepoint (_threat.py:1190ish) accepts any ENDORSE Boundary whose predicate string matches entry.mitigation -- no module joins a Boundary against observed code (grep confirmed only _models/__init__/_threat import both Boundary and effect-scanning, and _threat uses boundaries purely declaratively). Repro: may=sql node, an endorse boundary with predicate=parameterization on the only foreign inflow, and a weakness:CWE-89:<node> NoFlow claim -> THREAT003 PROVED with zero real parameterization in code. Fix direction: a SYS-family rule binding each ENDORSE boundary predicate to an observed sanitizer site in code=-bound files (analogous to SYS100), or at minimum require chokepoint boundaries to carry an evidence ref (code=/claim) selfconform verifies. Non-vacuous acceptance: a litmus where the claimed predicate has NO matching code site is REFUSED, plus the positive case where it does.