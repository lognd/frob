---
id: T-3456
title: Promote T-2114 (frob:tests directive)/diff-scoped ARCH001/CrossTicketLeakage
  from land-only assertions to real frob check/close gate rules
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: the too-broad glob accepted at creation collided with ~20
  other open tickets; this is a design/investigation-first ticket whose real fix location
  (a new frob.gates module vs extending _land_cmd.py/_land.py) is not yet decided
  -- see body for the concrete functions to reuse (T-3302's own investigation)
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: the too-broad glob accepted at creation collided with ~20 other open tickets;
    this is a design/investigation-first ticket whose real fix location (a new frob.gates
    module vs extending _land_cmd.py/_land.py) is not yet decided -- see body for
    the concrete functions to reuse (T-3302's own investigation)
  actor: logan
  at: '2026-08-29'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
