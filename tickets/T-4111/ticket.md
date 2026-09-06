---
id: T-4111
title: 'H3-1: a guard that only reads a lockout, with no reachable writer, is a control
  that fires on nothing'
state: queued
kind: invariant
origin: human
created: '2026-09-06'
priority: critical
blocked_by:
- T-4110
parent: T-4109
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_guard_closure.py
- tests/gates_suite/test_guard_closure.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/modules/gates.md
  reason: docs/modules/gates.md is a shared rule catalog with 345-warning closure
    and 8 overlapping tickets; drop from every leaf's declared scope, catalog entries
    land as a small unscoped doc append at close time
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-307 H3-1 (verbatim, quoted at the bottom of T-4109's body). A rate-limit-
style guard read a lockout state (retry_after_seconds-shaped) but the
consumer's only test proved the READ path by calling the write path
(record_failure) directly from the test, never from a real caller reachable
from a route. Nothing in the gate set distinguishes "the guard reads a
lockout" from "something in-tree actually writes one that this guard's own
class can see" -- a call-graph CLOSURE property, not a wiring-presence check.

VERIFIED/REFUTED against code before filing (the epic's own claim needed
checking, per the parent ticket's instruction): the epic asserts frob
"already has the resolver, since it is what WIRE001 uses." This is WRONG on
two counts, confirmed by reading src/frob/gates/_wire.py directly:
  1. WIRE001 does NOT use the shared call-graph resolver at all. Its own
     module docstring and _is_reached_outside_diff_tests's docstring say so
     explicitly: WIRE001 is "DELIBERATELY a text scan, not build_reference_
     graph/build_call_graph" -- a bare short-name-plus-paren scan.
  2. The reason given is structural, not incidental: build_reference_graph/
     build_call_graph (src/frob/graph/callgraph.py) resolve an edge ONLY
     when the callee is PRIVATE (leading underscore) -- "never a public
     symbol" is the resolver's own rule. WIRE001's motivating cases are
     PUBLIC symbols, which the resolver structurally cannot see, so WIRE001
     had to build its own text-scan substrate instead.
  DEAD001 (src/frob/gates/_dead_symbols.py, same module family) is the gate
  that actually DOES use build_reference_graph, but only for private
  symbols. A route-class reachability check needs closure over route
  HANDLERS (public, decorator-registered) and guard/record_failure call
  sites (which may be public too) -- outside what the existing resolver
  covers today. Do not assume the resolver "just works" for this; either
  extend frob.graph.callgraph to optionally resolve public-symbol edges (a
  real substrate change, its own risk) or build a bespoke, narrowly-scoped
  closure check the way WIRE001 did, rather than the way DEAD001 did. Decide
  and document which, in this ticket's own design note, before implementing.

Work:
- a frob:invariant-shaped check (or a new gate rule, e.g. INV-GUARD001):
  "every symbol whose body calls a retry_after_seconds(class, ...)-shaped
  lockout READ has at least one in-tree caller of the matching WRITE
  primitive (record_failure(class, ...)-shaped) for the same class,
  reachable from a route/entry-point in that class" -- this is a naming-
  convention-generic closure check (the read/write primitive names must be
  configurable, not hardcoded to the consumer's own symbol names)
- must positively distinguish "test calls the write directly" from "a
  non-test caller reaches the write from the same route class" -- the exact
  gap the consumer's own test disguised

Fixture note (READ BEFORE IMPLEMENTING): this rule concerns a route/guard/
lockout shape frob's own tree does not have. A must-fire/must-stay-quiet
fixture CANNOT be built from real frob source -- it must be a small synthetic
fixture package (a handful of files under the test directory only, not
wired into frob's own runtime) that defines: a guard reading the lockout
primitive, a route class, and either (a) no caller of the write primitive
reachable from that route (must-fire), (b) a real caller reachable from a
route in the same class (must-stay-quiet), or (c) a caller of the write
primitive that exists but is reachable only from a DIFFERENT route class
(third case -- must-fire, the closest-to-real false-negative shape: a
class-scoping bug, not a total-absence bug). FLAG EXPLICITLY in the Done
report that this leaf's fixture is synthetic-package-based, not drawn from
frob's own dogfood surface, per the parent epic's dogfooding-invisible
diagnosis.

frob:ticket T-4109