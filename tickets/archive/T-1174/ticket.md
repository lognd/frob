---
id: T-1174
title: 'arch: split remaining ~10 gate families out of src/frob/gates/__init__.py
  (8128 lines) -- T-1170 residue'
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
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates.py::TestOptInGates::test_dup_gate_off_by_default
- tests/test_gates.py::TestOptInGates::test_dup_gate_fires_on_planted_clone_when_enabled
- tests/test_gates.py::TestOptInGates::test_dup_gate_fails_closed_when_enforced_but_core_missing
designated_repro_test: null
threat: null
component: null
---
T-1170 extracted ONE cohesive family (DOC001/DOC002 -- `doclink_gate`/
`docanchor_gate` plus their private helpers) into
`src/frob/gates/_doclink_docanchor.py` (gates/__init__.py 8401 -> 8128
lines), one-family-per-land per the T-1072/T-1140/T-1159 discipline.
Budget did not allow the other ~10 remaining families this drive's own
ticket named. gates/__init__.py is still 8128 lines, well above the
large-file threshold.

Still remaining, in the same one-family-per-land shape:
- SYS00x/DOC003 (sys_gate + helpers, ~600 lines)
- DUP00x (dup_gate + helpers, ~500 lines)
- FUZZ00x (fuzz_gate)
- INV00x (inv006_gate + helpers)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1170 close
with silent residue, per TICK011.