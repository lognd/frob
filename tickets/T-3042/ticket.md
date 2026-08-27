---
id: T-3042
title: 'V-model H1: vmodel_check has zero callers and no authoring format, so the
  epic can complete without ever checking anything'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/parse/grammar_core.rs
- strata-core/src/parse/grammar_policy.rs
- src/frob/gates/_vmodel.py
- src/frob/check/__init__.py
- tests/unit/strata/test_vmodel_authoring.py
- tests/test_gates_vmodel.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/parse/grammar_core.rs
  reason: 'T-3042: additive vmodel_node/vmodel_edge authoring format in the strata
    grammar (T-3006 precedent) plus a WARN-severity VMOD001 gate wired into frob check'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/parse/grammar_policy.rs
  reason: 'T-3042: additive vmodel_node/vmodel_edge authoring format in the strata
    grammar (T-3006 precedent) plus a WARN-severity VMOD001 gate wired into frob check'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_vmodel.py
  reason: 'T-3042: additive vmodel_node/vmodel_edge authoring format in the strata
    grammar (T-3006 precedent) plus a WARN-severity VMOD001 gate wired into frob check'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'T-3042: additive vmodel_node/vmodel_edge authoring format in the strata
    grammar (T-3006 precedent) plus a WARN-severity VMOD001 gate wired into frob check'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/test_vmodel_authoring.py
  reason: 'T-3042: additive vmodel_node/vmodel_edge authoring format in the strata
    grammar (T-3006 precedent) plus a WARN-severity VMOD001 gate wired into frob check'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_gates_vmodel.py
  reason: 'T-3042: additive vmodel_node/vmodel_edge authoring format in the strata
    grammar (T-3006 precedent) plus a WARN-severity VMOD001 gate wired into frob check'
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
