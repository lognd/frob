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
