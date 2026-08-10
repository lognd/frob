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