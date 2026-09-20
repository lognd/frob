---
id: T-5104
title: 'strata kernel: module attribute on Node plus the kernel.md law-1 record of
  the deliberate growth (D-M4)'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-3964
parent: T-5081
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_models.py
- docs/strata/kernel.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.536.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
- field: sprint
  old_value: v0.536.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
designated_repro_test: null
acceptance:
- text: Given a node declared in a module, when elaborated, then its Node fact carries
    `module` equal to that file's module path, and a Datalog query over `module` returns
    the module's node set.
  evidence: []
- text: Given docs/strata/kernel.md, when read, then it contains a law-1 record naming
    the `module` attribute as the single deliberate kernel growth for the module system,
    with the refused alternatives (Module primitive, module-level flows, module trust
    levels).
  evidence: []
- text: 'Given the kernel primitive list, when counted after this change, then it
    is still exactly six (Node, Flow, Boundary, Bound, Claim, Scenario) -- positive
    control: a test asserts the primitive set is unchanged.'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Kernel change, exactly one attribute (owner decision D-M4). Add `module` to the
Node model in src/frob/strata/_models.py (class Node, ~line 381) so "which
module does node X live in" is a queryable fact rather than parser metadata --
the per-module audit and the two-sided `accepts` check both need it as a fact.
Nothing else is added: no Module primitive, no module-level flow, no module
trust level. Record the deliberate growth in docs/strata/kernel.md against
charter law 1 (the kernel grows deliberately or the feature is wrong): what was
added, why the six primitives were not enough, and what was explicitly refused.
