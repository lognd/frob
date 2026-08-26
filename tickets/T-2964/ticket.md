---
id: T-2964
title: 'Epic: cross-repo/multi-project portability of frob''s enforcement surface'
state: queued
kind: feature
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: epic
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2384/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Umbrella epic for cross-repo/multi-project portability of frob's
enforcement surface -- frob is deployed to sibling repos (lograder,
feldspar, and others) and needs its gates, schema resolvers, and
skills/agents sync machinery to work correctly against a project that
is not frob's own repo (different package name, different declared
source roots, its own frob.toml).

Filed as the correct top-level home for T-2384 (previously mis-parented
under T-1382, the unrelated Makefile-decoupling epic -- see T-2959's
Done report for the investigation). T-2384 and its own children
(T-2891, T-2892) already cover: retargeting hardcoded "src/frob/"
literals onto the project's own declared source roots (T-2195's
resolver), cooperative/provenance-aware sync-skills across multiple
frob-enabled repos, a durable meta-check (PORT001) against a second
hardcoded-path implementation reappearing, and fixing the 12
*SCHEMA-family-gates-render-UNRESOLVED-as-clean-pass gap.

No new acceptance criteria of its own beyond what T-2384 already
states and has met -- this ticket exists purely to give the portability
work tree a correctly-scoped parent, since frob's own `set-parent`
tooling has no route to clear a ticket's parent to null (T-2770's
`set_parent` only supports MOVING a parent edge to another existing
ticket, never detaching one to root -- see the follow-up ticket filed
for that tooling gap). Close this epic once T-2384's own tree is fully
verified terminal under it (already true today).
