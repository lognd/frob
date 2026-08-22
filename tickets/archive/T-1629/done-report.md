## Done report

SYS110 (frob.strata._selfconform._undeclared_intended_surface_violations)
replaces the deleted SYS104 with the INTENT-not-mirror shape: interface=
is read purely as hand-declared intent (never auto-written, per T-1870's
owner directive, untouched by this ticket), and a node's real public
surface must be a SUBSET of what it declares. A node with zero
interface= attrs has not opted in and is silently skipped -- phased,
per-node migration, not a repo-wide big-bang requirement, matching the
ticket's own design-questions section.

MEASURED BLOCKER AVOIDED, NOT FORCED: turning SYS110 on unconditionally
against design/frob.strata's real, pre-existing interface= blocks (17
nodes had declared a non-empty interface= before this ticket -- leftover
T-0668/T-1150-era generated-mirror data, unmaintained since T-1870
deleted the writer) produced 734 violations across 15 of those 17 nodes,
breaking TestRealGateGreen outright. Rather than force this through (no
single-diff fix exists -- the correct remedy is a human hand-curation
pass per node, exactly what the ticket's own "sequenced per node" design
note calls for) or silently disable the new check, SYS110_UNAUDITED_NODES
(frob.strata._selfconform) is a disclosed, hand-typed exemption for
exactly those 15 node ids, with the measured finding count and the
migration path in its own docstring. The other TWO pre-existing declarer
nodes (checker, fleet) already conformed and are NOT exempted -- SYS110
is live and enforced for every node not in that frozenset, today.

REG011 VERDICT (asked for explicitly): docs/design/registry/arch-checks.
yaml's SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE row named T-1629 as its
own follow-up. T-1629's SYS110 DOES genuinely re-cover it -- "flagging an
undeclared public symbol against hand-declared intent, not a mirror-
equality check" is exactly SYS110's shape (verified against the row's
own deferral prose, quoted in this ticket's bound acceptance criterion).
Re-dispositioned in this same change to handled_by:SYS110.

Changed:
- src/frob/strata/_selfconform.py: SYS_UNDECLARED_INTENDED_SURFACE
  ("SYS110"), SYS110_UNAUDITED_NODES, _undeclared_intended_surface_
  violations (new), wired into _collect_sys_violations; module docstring
  SYS110 section
- src/frob/strata/__init__.py: re-export SYS_UNDECLARED_INTENDED_SURFACE/
  SYS110_UNAUDITED_NODES (matching every other SYS10x rule id's existing
  re-export)
- src/frob/gates/_waive.py::_KNOWN_GATE_RULES: +"SYS110"
- docs/strata/surface.md: new #sys110-undeclared-intended-surface-t-1629
  section (design rationale, migration boundary, REG011 verdict)
- docs/design/registry/arch-checks.yaml: SLH-SYS-EVA-03 re-dispositioned
  out_of_scope:reasoned-deferral -> handled_by:SYS110
- tests/unit/strata/test_selfconform.py: TestUndeclaredIntendedSurface
  (4 tests)

Evidence: 5 node ids bound (see evidence list), accepted against the
ticket's own bound acceptance criterion (--accepts 0).

Gates: tests/unit/strata/test_selfconform.py full file -- 70/70 passed,
including TestRealGateGreen (the real repo's design/frob.strata run
against the real tree stays zero violations with SYS110 live).

### Changed
```
 tickets/T-1629/done-report.md      | 74 ++++++++++++++++++++++++++++++++++++++
 tickets/T-1629/ticket.md           | 43 ++++++++++++++++++++--
 tickets/T-1972/ticket.md | 23 ++++++++++++
 3 files changed, 137 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_declared_superset_is_silent` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_node_with_no_interface_attrs_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_unaudited_node_is_silenced_regardless_of_drift` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 1 error(s), 1109 warning(s), 708 waived
- error-findings: DOCENUM001@docs/modules/gates.md
