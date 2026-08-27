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
- strata-core/src/graph/query.rs
- src/frob/gates/_vmodel.py
- tests/test_gates_vmodel.py
- tests/unit/strata/test_vmodel_check.py
- strata-core/src/parse/grammar_core.rs
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
- op: add
  glob: strata-core/src/graph/query.rs
  reason: 'query.rs''s own test fixture constructs an EdgeKindSchema literal; adding

    the required_attrs field to that struct (T-3044 H3) is a mechanical

    compile-fix in the same struct''s other construction site, not new scope.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_vmodel.py
  reason: 'Extending the graph kernel''s node/edge attrs to construction-time

    validation directly changes vmodel_check''s data-in shape (the only PyO3

    consumer) -- its sole Python caller (frob.gates._vmodel) and both test

    files bound to vmodel_check via frob:tests must move in the same change

    or the gate breaks at runtime. The grammar/DSL surface for AUTHORING

    attrs in .strata files is explicitly left to a follow-up ticket (filed

    separately), not touched here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_gates_vmodel.py
  reason: 'Extending the graph kernel''s node/edge attrs to construction-time

    validation directly changes vmodel_check''s data-in shape (the only PyO3

    consumer) -- its sole Python caller (frob.gates._vmodel) and both test

    files bound to vmodel_check via frob:tests must move in the same change

    or the gate breaks at runtime. The grammar/DSL surface for AUTHORING

    attrs in .strata files is explicitly left to a follow-up ticket (filed

    separately), not touched here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: 'Extending the graph kernel''s node/edge attrs to construction-time

    validation directly changes vmodel_check''s data-in shape (the only PyO3

    consumer) -- its sole Python caller (frob.gates._vmodel) and both test

    files bound to vmodel_check via frob:tests must move in the same change

    or the gate breaks at runtime. The grammar/DSL surface for AUTHORING

    attrs in .strata files is explicitly left to a follow-up ticket (filed

    separately), not touched here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/_vmodel.py
  reason: 'Extending the graph kernel''s node/edge attrs to construction-time

    validation directly changes vmodel_check''s data-in shape (the only PyO3

    consumer) -- its sole Python caller (frob.gates._vmodel) and both test

    files bound to vmodel_check via frob:tests must move in the same change

    or the gate breaks at runtime. The grammar/DSL surface for AUTHORING

    attrs in .strata files is explicitly left to a follow-up ticket (filed

    separately), not touched here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/test_gates_vmodel.py
  reason: 'Extending the graph kernel''s node/edge attrs to construction-time

    validation directly changes vmodel_check''s data-in shape (the only PyO3

    consumer) -- its sole Python caller (frob.gates._vmodel) and both test

    files bound to vmodel_check via frob:tests must move in the same change

    or the gate breaks at runtime. The grammar/DSL surface for AUTHORING

    attrs in .strata files is explicitly left to a follow-up ticket (filed

    separately), not touched here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: tests/unit/strata/test_vmodel_check.py
  reason: 'Extending the graph kernel''s node/edge attrs to construction-time

    validation directly changes vmodel_check''s data-in shape (the only PyO3

    consumer) -- its sole Python caller (frob.gates._vmodel) and both test

    files bound to vmodel_check via frob:tests must move in the same change

    or the gate breaks at runtime. The grammar/DSL surface for AUTHORING

    attrs in .strata files is explicitly left to a follow-up ticket (filed

    separately), not touched here.

    '
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/src/parse/grammar_core.rs
  reason: 'Fixing the existing gate/test regression from H3''s kernel change requires

    letting a human actually AUTHOR the new required attrs in the .strata

    surface grammar (optional runnable/code_ref/reason clauses on

    vmodel_node/vmodel_edge) -- otherwise every real vmodel_node declaration

    becomes permanently unconstructible and the existing gate tests (which

    assert specific closure outcomes on real .strata text) cannot be fixed at

    all without this. Kept minimal: three fixed optional clauses, not a

    general attr syntax (that generalization is T-3049''s canonical-schema

    scope).

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
