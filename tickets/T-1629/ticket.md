---
id: T-1629
title: 'strata: interface= should declare INTENDED surface, not mirror every public
  symbol'
state: queued
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
- src/frob/strata/**
- tests/unit/strata/test_selfconform.py
- docs/strata/surface.md
- src/frob/gates/_waive.py
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
designated_repro_test: null
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