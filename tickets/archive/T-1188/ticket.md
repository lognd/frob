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
- tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
designated_repro_test: null
evidence_changes:
- old_node: tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_with_bound_invariant_anchor_is_silent
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
  reason: T-1763 deleted INV006 and TestInv006Gate; rebinding to INV003's equivalent
    still-live test
  actor: logan
  at: '2026-08-07'
- old_node: tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim
  new_node: tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_with_bound_known_invariant_is_silent
  reason: T-1763 deleted find_carried_waiver/_inv006_split_assist.py entirely along
    with INV006 -- no functional equivalent exists; rebinding to the nearest still-live
    sibling test in INV003
  actor: logan
  at: '2026-08-07'
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

## Done report

Extracted the INV00x invariant-coverage gate family (invariant_gate/INV001-
INV002-INV005, inv003_gate, inv004_gate, inv006_gate, plus all their private
helpers and the INV003_SPEC_DIRS/INV006_SRC_DIRS/INV006_SRC_SUFFIXES
constants) out of gates/__init__.py into a new src/frob/gates/_inv.py
(636 -> module lines), mirroring _sys.py's T-1187 precedent: the four gate
functions stay re-exported from frob.gates unchanged, everything else is
private to the new module.

Two generic evidence-matching helpers (_evidence_collected,
_node_id_matches_symref) stay in __init__.py, shared with the TEST00x
family still living there -- _inv.py imports them via a function-local
import (not module-level) specifically to avoid a __init__ <-> _inv
circular import, since __init__ itself imports _inv at its own import
time.

`frob sys sync-interface` picked up the three relocated constants as
newly-scanned public symbols on the `gates` design node (SYS104) and wrote
the missing `attr interface=` entries into design/frob.strata; scope was
extended to include that file for the same reason. Doc-linked frob:tests/
frob:describes directives referencing these six symbols in
docs/modules/gates.md and tests/test_gates.py were repointed from
`gates/__init__.py::<name>` to `gates/_inv.py::<name>`.

gates/__init__.py: 7310 -> 6669 lines (still well above the 800-line
threshold; ~6 families + the run_gates spine remain per T-1188's own
residue list -- this is one family per the established discipline, not
the terminal split).

### Changed
```
 tickets.md | 21 +++++++++++++++++++--
 1 file changed, 19 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestInvariantGate::test_inv001_no_evidence` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantGate::test_inv001_passes_with_collected_evidence` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantGate::test_inv001_collected_but_unbound_evidence_warns_inv005` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInvariantGate::test_inv002_no_anchor` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv003Gate::test_exclusivity_claim_without_marker_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv004Gate::test_section_with_normative_language_and_no_invariant_is_advisory` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_in_source_without_anchor_warns` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006Gate::test_exclusivity_claim_with_bound_invariant_anchor_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestInv006SplitAssist::test_finds_carried_waiver_for_verbatim_moved_claim` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: 0 error(s), 730 warning(s), 672 waived
- error-findings: none (measured, zero errors)
