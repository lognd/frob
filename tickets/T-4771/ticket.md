---
id: T-4771
title: Node base with a react-frontend facet, and a unity base in adopt-in-place mode
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4765
parent: T-4757
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/bases/node/**
- src/frob/scaffold/data/bases/unity/**
- src/frob/scaffold/data/facets/react-frontend/**
- src/frob/scaffold/data/types/web-app/**
- src/frob/scaffold/data/types/unity-project/**
- src/frob/scaffold/_unity_project.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: Given the web-app preset, when its rendered frob.toml is compared against
    the shared one, then it is the same file, not a fork
  evidence: []
- text: Given the unity base, when the type listing is printed and the base is rendered
    from the CLI, then both succeed
  evidence: []
- text: Given the web-app preset, when frob check runs in the rendered tree, then
    it is clean
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Introduce the node BASE and make unity reachable.

web-app becomes node plus a react-frontend facet plus github-ci plus
docs-site. Its frob.toml is 90 percent a duplicate of the shared python one
with the refs block dropped (12 REF001) and its CI workflow 73 percent,
including a comment that points at the file it was cloned FROM -- the
definition of drift by copy.

unity-project exists only as a Python function and is not registered: the
new verb errors that the type is not registered and the list verb shows
seven types, not eight. Under base plus facets it is the unity base in
adopt-in-place mode, which is exactly the primitive the planned add verb
needs anyway (apply facets to an existing tree). T-4578 is already queued to
wire the CLI form; CHECK ITS STATE FIRST and build on it rather than
re-doing it -- this leaf owns the base-plus-facets decomposition, not the
CLI wiring.

Also fix the two measured web-app packaging defects while in the manifest,
if T-3805 and T-3806 have not already landed: check both before touching
package.json.

Positive controls:
1. the rendered web-app frob.toml is the shared one, asserted by comparison;
2. the unity base is listed by the type listing and renders from the CLI;
3. frob check clean on the web-app preset.
