---
id: T-1170
title: 'arch: split remaining ~11 gate families out of src/frob/gates/__init__.py
  (8349 lines) -- T-1159 residue'
state: done
kind: feature
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
- src/frob/gates/_fix_engine.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: lazy cross-module import of _doc_anchor_slugs must repoint at its new home
    src/frob/gates/_doclink_docanchor.py after the T-1170 split
  actor: logan
  at: '2026-07-28'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS104 interface= sync for new gates/_doclink_docanchor.py
    module
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestDoclinkGate::test_orphan_doc_is_error_and_linked_docs_pass
- tests/test_gates.py::TestDocanchorGate::test_resolvable_heading_and_explicit_anchor_pass
- tests/test_gates.py::TestFixEngineTierA::test_doc002_unique_fuzzy_candidate_rewritten_and_reverifies_clean
designated_repro_test: null
threat: null
component: null
---
T-1159 extracted the DEC00x/COMPLIANCE00x family (decisions_gate,
compliance_gate, _compliance005_violation) into
src/frob/gates/_decisions_compliance.py (gates/__init__.py 8554 -> 8349
lines), one cohesive family per land per the standing discipline
(T-1072/T-1077/T-1140 precedent: verbatim moves, directives intact, lazy
call-time imports, re-export only externally-called names, carried
INV006 waivers, PII012 re-keys, design/frob.strata interface= sync via
frob sys sync-interface).

Filed honestly per T-1129's own TICK011 gate (which this residue itself
now enforces): T-1159's own acceptance criterion named ~12 remaining
families (SCOPE/PREWORK, INV00x, TEST00x, SYS00x/DOC00x, DUP00x, REL00x,
FUZZ00x, DOCLINK/DOCANCHOR, PERF, run_gates spine, COV00x) and this land
only had budget for one. gates/__init__.py is still 8349 lines, well
above the 800-line large-file threshold (ARCH102-adjacent) T-1159's
acceptance criterion targets -- the remaining families are the real
residue, not done.

Follow-up work, in the same one-family-per-land shape T-1159 established:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines, adjacent to the
  COMPLIANCE family this land just moved -- natural next split)
- DUP00x (dup_gate + helpers, ~500 lines)
- FUZZ00x (fuzz_gate)
- DOCLINK/DOCANCHOR (doclink_gate, docanchor_gate)
- INV00x (inv006_gate + helpers -- note _inv006_split_assist.py already
  holds T-1134's carry-waiver detector separately; the gate function
  itself is still in __init__.py)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time
  rather than assuming

Each remaining family should get its own ticket sized to "one cohesive
land" the way this one was, not one giant ticket -- but re-filing T-1159
itself (re-titled to name only the STILL-remaining families) is simplest
and avoids re-deriving the acceptance criteria/discipline notes from
scratch.