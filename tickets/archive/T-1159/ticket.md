---
id: T-1159
title: 'arch: split remaining ~12 gate families out of src/frob/gates/__init__.py
  (8408 lines) -- T-1140 residue'
state: done
kind: feature
origin: agent
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
- tests/test_decisions.py
- docs/modules/decisions.md
- docs/design/registry/EXHAUSTIVENESS-GATE.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_decisions.py
  reason: T-1159 verbatim-moves decisions_gate/compliance_gate to a new file; their
    frob:tests/frob:describes back-references and AFFECT001-touched doc all need updating
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/decisions.md
  reason: T-1159 verbatim-moves decisions_gate/compliance_gate to a new file; their
    frob:tests/frob:describes back-references and AFFECT001-touched doc all need updating
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/design/registry/EXHAUSTIVENESS-GATE.md
  reason: T-1159 verbatim-moves decisions_gate/compliance_gate to a new file; their
    frob:tests/frob:describes back-references and AFFECT001-touched doc all need updating
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: sys sync-interface writes interface=compliance_gate (newly present in gates
    __all__)
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_decisions.py::test_dec001_dangling_decision_edge
- tests/test_gates.py::TestComplianceGate::test_compliance005_real_repo_registry_passes
designated_repro_test: null
acceptance:
- text: GIVEN src/frob/gates/__init__.py WHEN the remaining families (SCOPE/PREWORK,
    INV00x, TEST00x, DECISIONS, COMPLIANCE00x, SYS00x/DOC00x, DUP00x, REL00x, FUZZ00x,
    DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) are extracted one cohesive family
    per land THEN gates/__init__.py drops below the 800-line large-file threshold
    with no public API change and all existing tests pass
  evidence:
  - tests/test_decisions.py::test_dec001_dangling_decision_edge
threat: null
component: null
---
T-1140 extracted the TICK00x family (gates/__init__.py 9172 -> 8408) and disclosed the ~12 remaining families in its done report WITHOUT filing a residue ticket (fourth disclosed-cut-without-ticket incident -- T-1129's gate is the systemic fix; coordinator refiled this one). Same T-1072/T-1077/T-1140 discipline: verbatim moves, directives intact, lazy call-time imports, re-export only externally-called names, carried INV006 waivers, PII012 re-keys, and design/frob.strata interface= sync now via frob sys sync-interface (T-1150).