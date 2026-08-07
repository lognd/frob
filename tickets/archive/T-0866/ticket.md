---
id: T-0866
title: 'typestate declaration surface: module/object protocol declarations + init/deinit
  pair inference'
state: dropped
kind: security
origin: human
created: '2026-07-23'
priority: high
parent: T-0739
tier: ticket
sprint: null
scope:
- src/frob/graph/dsl.py
- src/frob/arch/_typestate.py
- docs/design/typestate.md
- tests/unit/test_typestate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: GIVEN a module declaring an explicit protocol (states, transitions, per-function
    state requirements) WHEN the declaration is parsed THEN the model exposes the
    machine to downstream checks with source locations
  evidence: []
- text: GIVEN a module with foo_init/foo_deinit and no explicit declaration WHEN inference
    runs THEN the init/deinit pair protocol is inferred, and no inference happens
    for any non-pair machine
  evidence: []
threat: null
component: arch
---
T-0739 child 1 (declaration surface). The typestate declaration surface: how a protocol is declared for (a) module/subsystem singleton protocols and (b) declared object protocols. Includes the name-pattern-inferred init/deinit convenience pair (inference ONLY for the common *_init/*_deinit pair, never for general machines) and the explicit declared-state-machine form (states, transitions, functions-valid-in-state). Deliverable: the parsed declaration model + directives/DSL wiring, consumed by the verification child. No enforcement in this ticket.

## Drop reason
- 2026-07-23: duplicate of the pre-existing T-0739 child set (T-0744/T-0745/T-0746/T-0747, mostly done) -- filed 2026-07-23 without checking parent-edge children; typestate declaration surface, summary engine, verification+excuses already delivered in graph/dsl.py, graph/summary.py, gates/_protocol_summary.py