---
id: T-1629
title: 'strata: interface= should declare INTENDED surface, not mirror every public
  symbol'
state: done
kind: feature
origin: human
created: '2026-08-05'
priority: high
blocked_by:
- T-1625
- T-1870
parent: T-1623
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
- tests/unit/strata/test_selfconform.py
- docs/strata/surface.md
- src/frob/gates/_waive.py
- src/frob/strata/_selfconform.py
- src/frob/strata/__init__.py
- docs/design/registry/arch-checks.yaml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: tests/**, docs/** and src/frob/gates/** are mega-globs and scope IS the
    lease; as written this ticket would lock the fleet out of the entire docs and
    tests trees. Narrowed to the interface-surface doc and the selfconform test it
    actually touches.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: docs/**
  reason: tests/**, docs/** and src/frob/gates/** are mega-globs and scope IS the
    lease; as written this ticket would lock the fleet out of the entire docs and
    tests trees. Narrowed to the interface-surface doc and the selfconform test it
    actually touches.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/gates/**
  reason: tests/**, docs/** and src/frob/gates/** are mega-globs and scope IS the
    lease; as written this ticket would lock the fleet out of the entire docs and
    tests trees. Narrowed to the interface-surface doc and the selfconform test it
    actually touches.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: tests/**, docs/** and src/frob/gates/** are mega-globs and scope IS the
    lease; as written this ticket would lock the fleet out of the entire docs and
    tests trees. Narrowed to the interface-surface doc and the selfconform test it
    actually touches.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/surface.md
  reason: tests/**, docs/** and src/frob/gates/** are mega-globs and scope IS the
    lease; as written this ticket would lock the fleet out of the entire docs and
    tests trees. Narrowed to the interface-surface doc and the selfconform test it
    actually touches.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/gates/_waive.py
  reason: tests/**, docs/** and src/frob/gates/** are mega-globs and scope IS the
    lease; as written this ticket would lock the fleet out of the entire docs and
    tests trees. Narrowed to the interface-surface doc and the selfconform test it
    actually touches.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/strata/**
  reason: src/frob/strata/** matches 71 files (>25) -- narrow to the one file this
    ticket's new SYS110 check lives in
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: src/frob/strata/** matches 71 files (>25) -- narrow to the one file this
    ticket's new SYS110 check lives in
  actor: logan
  at: '2026-08-10'
- op: add
  glob: src/frob/strata/__init__.py
  reason: re-export SYS_UNDECLARED_INTENDED_SURFACE/SYS110_UNAUDITED_NODES for tests,
    matching every other SYS10x rule id's existing re-export convention
  actor: logan
  at: '2026-08-10'
- op: add
  glob: docs/design/registry/arch-checks.yaml
  reason: re-disposition SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE to handled_by:SYS110,
    the ticket's own bound acceptance criterion
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_declared_superset_is_silent
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_node_with_no_interface_attrs_is_skipped
- tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_unaudited_node_is_silenced_regardless_of_drift
- tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
designated_repro_test: null
acceptance:
- text: Given SLH-SYS-EVA-03-UNDECLARED-PUBLIC-SURFACE (docs/design/registry/arch-checks.yaml)
    was re-dispositioned to out_of_scope:reasoned-deferral when T-1870 deleted SYS104,
    when this ticket ships its replacement rule (the hand-declared-intent enforcement
    check), then re-disposition SLH-SYS-EVA-03 to handled_by:<that new rule id> so
    the deferral does not orphan -- a deferral pointing at a ticket that no longer
    exists would be the same catalogued-but-unenforced shape this repo already paid
    for once
  evidence:
  - tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_real_symbol_outside_declared_set_fires
  - tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_declared_superset_is_silent
  - tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_node_with_no_interface_attrs_is_skipped
  - tests/unit/strata/test_selfconform.py::TestUndeclaredIntendedSurface::test_unaudited_node_is_silenced_regardless_of_drift
  - tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
`interface=` is currently a GENERATED MIRROR of each node's entire public surface, maintained by `frob sys sync-interface` and enforced by SYS104 ("public symbol exported by code but not declared in interface=").

A generated mirror cannot be violated in any meaningful sense: when code and declaration disagree, the fix is to regenerate the declaration. So the only thing SYS104 actually catches is "you added a public symbol and did not run sync-interface" -- bookkeeping, not architecture. It can never answer the question an interface declaration exists to answer: is this symbol SUPPOSED to be public?

The valuable form is the inverse. Declare the INTENDED surface by hand -- normally small -- and have the gate fail on anything public beyond it. Then adding a new public symbol is a deliberate act that requires editing the contract, and accidental surface growth (the actual architectural risk) becomes a build failure instead of a regeneration prompt.

That inversion also fixes the size problem from the other end: an intended surface for `core` is a handful of entry points, not 817 symbols.

Design questions the ticket must settle:
- Migration path: today's generated lists are the starting point, but a mechanical copy would enshrine the current sprawl as "intended". Each node's list needs a human pass to distinguish real contract from incidental exposure. That is the actual work, and it should be sequenced per node rather than attempted in one sweep.
- What replaces sync-interface: probably a `--suggest` mode that reports undeclared public symbols for a human to accept or refactor away, rather than silently writing them in.
- Interaction with the SYS104 self-audit family, which currently reads the generated form.

This is the deepest of the strata maturity tickets and should be sequenced after the mechanical ones (duplicate blocks, testsuite noise), since those shrink the surface this has to reason about.

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
