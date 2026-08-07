---
id: T-1188
title: 'arch: split remaining ~7 gate families out of src/frob/gates/__init__.py (7309
  lines) -- T-1187 residue'
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
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: frob sys sync-interface wrote gates node interface entries for the three
    INV006/INV003 constants this split relocated to _inv.py
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_gates.py::TestInvariantGate::test_inv001_no_evidence
- tests/test_gates.py::TestInvariantGate::test_inv001_passes_with_collected_evidence
- tests/test_gates.py::TestInvariantGate::test_inv001_collected_but_unbound_evidence_warns_inv005
- tests/test_gates.py::TestInvariantGate::test_inv002_no_anchor
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
- tests/test_gates.py::TestInv004Gate::test_section_with_normative_language_and_no_invariant_is_advisory
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns
- tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_with_bound_invariant_anchor_is_silent
- tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
designated_repro_test: null
threat: null
component: null
---
T-1187 extracted ONE more cohesive family (SYS00x/DOC003/SELFAUDIT001 --
sys_gate plus its private helpers) into src/frob/gates/_sys.py
(gates/__init__.py 7960 -> 7309 lines), continuing the
T-1072/T-1140/T-1159/T-1170/T-1174/T-1183/T-1187 one-family-per-land
discipline. Budget did not allow the other ~7 remaining families this
ticket's own body named. gates/__init__.py is still 7309 lines, well
above the large-file threshold.

Still remaining, in the same one-family-per-land shape:
- INV00x (inv006_gate + helpers, inv003_gate/inv004_gate/invariant_gate)
- TEST00x (test policy loading + TEST00x gate family)
- REL00x (release-bump/debt gate wiring)
- PERF (perf gate wiring, distinct from frob.perf's own module)
- COV00x (coverage gate family)
- SCOPE/PREWORK (scope_gate, prework_gate)
- the run_gates spine itself (_assemble_gate_report, _build_jobs,
  run_gates) -- likely stays in __init__.py as the module's own
  orchestration root, but worth an explicit decision at design time

Re-filed (not re-derived from scratch) rather than letting T-1187 close
with silent residue, per TICK011.