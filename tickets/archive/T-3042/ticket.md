---
id: T-3042
title: 'V-model H1: vmodel_check has zero callers and no authoring format, so the
  epic can complete without ever checking anything'
state: done
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
- strata-core/src/parse/mod.rs
- src/frob/gates/__init__.py
- docs/strata/vmodel.md
- editors/vscode-strata/syntaxes/strata.tmLanguage.json
- docs/guides/extending/strata-surface-grammar.md
- strata-core/strata_core.pyi
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
- op: add
  glob: strata-core/src/parse/mod.rs
  reason: 'T-3042: vmodel_node/vmodel_edge parse fixtures (must-fire duplicate check,
    round-trip, additive-parse regression, cross-file-not-resolved-here) live in this
    module test block, same as T-3006 precedent'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'T-3042: register vmodel_gate in the _ALL_GATES/_CANONICAL_GATE_ORDER/_build_jobs
    job table (gates/__init__.py) so VMOD001 is reachable via frob check --only vmodel,
    plus a new docs section for the authoring format and gate wiring (T-3009 released
    its lease on both files)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/strata/vmodel.md
  reason: 'T-3042: register vmodel_gate in the _ALL_GATES/_CANONICAL_GATE_ORDER/_build_jobs
    job table (gates/__init__.py) so VMOD001 is reachable via frob check --only vmodel,
    plus a new docs section for the authoring format and gate wiring (T-3009 released
    its lease on both files)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: editors/vscode-strata/syntaxes/strata.tmLanguage.json
  reason: 'T-3042: register vmodel_node/vmodel_edge (and their kind/level/src/dst
    clause keywords) in the syntax-highlighting grammar per this guides recipe, and
    update the affects-closure doc for parse_program (AFFECT001)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: docs/guides/extending/strata-surface-grammar.md
  reason: 'T-3042: register vmodel_node/vmodel_edge (and their kind/level/src/dst
    clause keywords) in the syntax-highlighting grammar per this guides recipe, and
    update the affects-closure doc for parse_program (AFFECT001)'
  actor: logan
  at: '2026-08-26'
- op: add
  glob: strata-core/strata_core.pyi
  reason: 'T-3042: vmodel_check has no type stub at all (a pre-existing T-3007 gap,
    exposed only now that this ticket adds its first real Python caller) -- ty check
    refuses the new caller without it'
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_gates_vmodel.py::TestVmodelGate::test_noop_no_design_dir
- tests/test_gates_vmodel.py::TestVmodelGate::test_noop_no_vmodel_declarations
- tests/test_gates_vmodel.py::TestVmodelGate::test_fires_vmod001_on_construction_error
- tests/test_gates_vmodel.py::TestVmodelGate::test_fires_vmod001_on_closure_violation
- tests/test_gates_vmodel.py::TestVmodelGate::test_quiet_on_a_genuinely_closed_graph
- tests/test_gates_vmodel.py::TestVmodelGate::test_spans_multiple_files
- tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_vmodel_node_and_edge_round_trip_through_python
- tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_duplicate_vmodel_node_name_is_a_parse_error
- tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_existing_bare_module_files_parse_unchanged
- tests/unit/strata/test_vmodel_authoring.py::TestVmodelAuthoringFormat::test_designs_own_frob_strata_still_parses
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: bd9da6c24206dc77f55ff5bb2f2f6a0ba88574fa
---
