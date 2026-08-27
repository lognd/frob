---
id: T-3044
title: 'V-model H3: graph nodes carry no payload -- test nodes bind to nothing runnable,
  artifacts bind to no code, supersedes cannot carry a reason'
state: queued
kind: bug
origin: human
created: '2026-08-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- strata-core/src/graph/model.rs
- strata-core/src/graph/vmodel.rs
- strata-core/src/graph/mod.rs
- strata-core/src/lib.rs
- strata_core.pyi
- docs/strata/vmodel.md
- docs/strata/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: strata-core/src/graph/model.rs
  reason: 'H3 payload work is contained to the generic graph kernel (node/edge attrs

    plus construction-time required-attr validation) and the V-model schema

    layer that declares which kinds require which attrs, plus the PyO3

    boundary function and its stub that expose node/edge data to Python.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/graph/vmodel.rs
  reason: 'H3 payload work is contained to the generic graph kernel (node/edge attrs

    plus construction-time required-attr validation) and the V-model schema

    layer that declares which kinds require which attrs, plus the PyO3

    boundary function and its stub that expose node/edge data to Python.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/graph/mod.rs
  reason: 'H3 payload work is contained to the generic graph kernel (node/edge attrs

    plus construction-time required-attr validation) and the V-model schema

    layer that declares which kinds require which attrs, plus the PyO3

    boundary function and its stub that expose node/edge data to Python.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/lib.rs
  reason: 'H3 payload work is contained to the generic graph kernel (node/edge attrs

    plus construction-time required-attr validation) and the V-model schema

    layer that declares which kinds require which attrs, plus the PyO3

    boundary function and its stub that expose node/edge data to Python.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata_core.pyi
  reason: 'H3 payload work is contained to the generic graph kernel (node/edge attrs

    plus construction-time required-attr validation) and the V-model schema

    layer that declares which kinds require which attrs, plus the PyO3

    boundary function and its stub that expose node/edge data to Python.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/vmodel.md
  reason: 'H3 payload work is contained to the generic graph kernel (node/edge attrs

    plus construction-time required-attr validation) and the V-model schema

    layer that declares which kinds require which attrs, plus the PyO3

    boundary function and its stub that expose node/edge data to Python.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/graph.md
  reason: 'H3 payload work is contained to the generic graph kernel (node/edge attrs

    plus construction-time required-attr validation) and the V-model schema

    layer that declares which kinds require which attrs, plus the PyO3

    boundary function and its stub that expose node/edge data to Python.

    '
  actor: logan
  at: '2026-08-26'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
