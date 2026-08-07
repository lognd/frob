---
id: T-1187
title: 'arch: split remaining ~8 gate families out of src/frob/gates/__init__.py (7960
  lines) -- T-1183 residue'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- docs/modules/gates.md
- tests/test_gates.py
- docs/strata/surface.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/strata/surface.md
  reason: T-1187's sys_gate split leaves this doc's frob:describes edge pointing at
    the old __init__.py location; a 1-line symref fix, same class as the tests/test_gates.py
    fixes already in scope
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestSysGate::test_noop_no_design_dir
- tests/test_gates.py::TestSysGate::test_sys001_dangling
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_folds_selfconform_violation
- tests/test_gates.py::TestSelfAuditGate::test_selfaudit001_clean_model_no_violations
designated_repro_test: null
threat: null
component: null
---
T-1183 extracted ONE more cohesive family (FUZZ001/002/003 -- fuzz_gate
plus its private helpers _fuzz_enforce/_fuzz_gate_violations) into
src/frob/gates/_fuzz.py (gates/__init__.py 8015 -> 7960 lines),
continuing the T-1072/T-1140/T-1159/T-1170/T-1174 one-family-per-land
discipline. Budget did not allow the other ~8 remaining families this
ticket's own body named. gates/__init__.py is still 7960 lines, well
above the large-file threshold.

Still remaining, in the same one-family-per-land shape:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines)
- INV00x (inv006_gate + helpers)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1183 close
with silent residue, per TICK011.