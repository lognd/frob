---
id: T-1623
title: 'strata maturity: make capability enforcement watertight'
state: queued
kind: security
origin: human
created: '2026-08-05'
priority: critical
parent: null
tier: epic
sprint: null
runs_last: false
scope:
- design/frob.strata
- src/frob/strata/**
- docs/strata/kernel.md
- docs/strata/selfconform.md
- src/frob/vet/_capability.py
- src/frob/vet/_capability_core.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_capability_modes.py
- tests/unit/strata/test_selfconform.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: docs/**
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: tests/**
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: remove
  glob: src/frob/vet/**
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/kernel.md
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: docs/strata/selfconform.md
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/vet/_capability.py
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/vet/_capability_core.py
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/vet/_capability_scan.py
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: src/frob/vet/_capability_modes.py
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
- op: add
  glob: tests/unit/strata/test_selfconform.py
  reason: T-1623 carried docs/** and tests/** mega-globs; scope IS the lease, so starting
    it as written would lock the whole fleet out of the docs and tests trees. Narrowed
    to the capability-enforcement surface it actually touches so it can be dispatched
    alongside other agents.
  actor: logan
  at: '2026-08-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
Umbrella for the strata self-model hardening reviewed on 2026-08-05. Findings, in dependency order: the declaration file is half redundancy (duplicate attr blocks, 5277 test names declared as interface); interface= is a generated mirror that cannot be meaningfully violated; capability detection is lexical rather than symbol-resolved; and via grants whole FILES rather than single controllable locations, with permission lists that only ever grow. Children carry the detail. Sequence the mechanical cleanups first so the design work reasons over a smaller surface.