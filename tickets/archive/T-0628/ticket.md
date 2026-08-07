---
id: T-0628
title: frob graph affects CLI subcommand + digest-drift gate (T-0325 follow-on)
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0325
tier: ticket
sprint: null
scope:
- src/frob/app/graph_runner.py
- src/frob/gates/**
- docs/modules/graph.md
- src/frob/app/config.py
- src/frob/app/app.py
- src/frob/__main__.py
- README.md
- tests/test_graph_affects_runner.py
- docs/modules/gates.md
- src/frob/check/__init__.py
- tests/test_gates_affect_drift.py
- docs/modules/app.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/app/config.py
  reason: 'A `frob graph affects` CLI subcommand needs the standard App/AppConfig

    argparse wiring trio (Subcommand enum + AppConfig fields in config.py,

    parser registration in __main__.py, runner-module registration in app.py)

    plus the README command-table row (DOC005 drift-lock), same pattern as

    T-0638''s `frob deprecated` land. The original ticket scope only listed the

    runner file itself; widening to cover the wiring call sites.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/app/app.py
  reason: 'A `frob graph affects` CLI subcommand needs the standard App/AppConfig

    argparse wiring trio (Subcommand enum + AppConfig fields in config.py,

    parser registration in __main__.py, runner-module registration in app.py)

    plus the README command-table row (DOC005 drift-lock), same pattern as

    T-0638''s `frob deprecated` land. The original ticket scope only listed the

    runner file itself; widening to cover the wiring call sites.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/__main__.py
  reason: 'A `frob graph affects` CLI subcommand needs the standard App/AppConfig

    argparse wiring trio (Subcommand enum + AppConfig fields in config.py,

    parser registration in __main__.py, runner-module registration in app.py)

    plus the README command-table row (DOC005 drift-lock), same pattern as

    T-0638''s `frob deprecated` land. The original ticket scope only listed the

    runner file itself; widening to cover the wiring call sites.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: README.md
  reason: 'A `frob graph affects` CLI subcommand needs the standard App/AppConfig

    argparse wiring trio (Subcommand enum + AppConfig fields in config.py,

    parser registration in __main__.py, runner-module registration in app.py)

    plus the README command-table row (DOC005 drift-lock), same pattern as

    T-0638''s `frob deprecated` land. The original ticket scope only listed the

    runner file itself; widening to cover the wiring call sites.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_graph_affects_runner.py
  reason: 'A `frob graph affects` CLI subcommand needs the standard App/AppConfig

    argparse wiring trio (Subcommand enum + AppConfig fields in config.py,

    parser registration in __main__.py, runner-module registration in app.py)

    plus the README command-table row (DOC005 drift-lock), same pattern as

    T-0638''s `frob deprecated` land. The original ticket scope only listed the

    runner file itself; widening to cover the wiring call sites.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/modules/gates.md
  reason: 'A `frob graph affects` CLI subcommand needs the standard App/AppConfig

    argparse wiring trio (Subcommand enum + AppConfig fields in config.py,

    parser registration in __main__.py, runner-module registration in app.py)

    plus the README command-table row (DOC005 drift-lock), same pattern as

    T-0638''s `frob deprecated` land. The original ticket scope only listed the

    runner file itself; widening to cover the wiring call sites.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: src/frob/check/__init__.py
  reason: 'New gate names must be added to a frob check --only stage group

    (_STAGE_GROUPS in src/frob/check/__init__.py) or

    TestCheckStageGroups.test_available_stages_cover_every_gate_and_tool fails --

    registering "affect_drift" in frob.gates._ALL_GATES without also listing it

    in gates-fast leaves it uncoverable by any --only group, which that test

    catches mechanically. Widening scope to the one dict literal that needs the

    new entry.

    '
  actor: logan
  at: '2026-07-26'
- op: add
  glob: tests/test_gates_affect_drift.py
  reason: New AFFECT001/AFFECT002 gate needs direct unit test coverage for close's
    TEST00x gate, same pattern as tests/test_graph_affects.py
  actor: logan
  at: '2026-07-26'
- op: add
  glob: docs/modules/app.md
  reason: 'AFFECT001 (this ticket''s own new gate) correctly flagged that config.py/graph_runner.py
    changes touch docs/modules/app.md#config and #runners obligations; updating that
    doc to describe the new affects subcommand/fields is the real fix, not a waive'
  actor: logan
  at: '2026-07-26'
evidence:
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_affects_requires_ref
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_affects_unresolvable_ref_exits_1
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_human_mode_reports_dependents_docs_tests
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_json_mode_payload
- tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_truncated_closure_flagged
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_no_closure_is_silent
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_stale_dependent_doc_flagged
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_stale_dependent_code_flagged
- tests/test_gates_affect_drift.py::TestAffectDriftGate::test_clean_when_closure_also_touched
designated_repro_test: null
acceptance:
- text: GIVEN a symbol with dependents WHEN frob graph affects SYMREF runs THEN the
    affected code/docs/tests print with truncation flagged; GIVEN a diff changing
    a symbol whose affects-closure docs were untouched WHEN the drift gate runs THEN
    it reports the stale dependents
  evidence:
  - tests/test_graph_affects_runner.py::TestGraphAffectsRunner::test_truncated_closure_flagged
  - tests/test_gates_affect_drift.py::TestAffectDriftGate::test_stale_dependent_doc_flagged
  - tests/test_gates_affect_drift.py::TestAffectDriftGate::test_stale_dependent_code_flagged
threat: null
component: null
---
T-0325 landed the warm affects() library query and frob_affects MCP tool but cut two surfaces as out of scope, noting them only in docs/modules/graph.md prose: (a) a frob graph affects REF CLI subcommand in src/frob/app/graph_runner.py so the north-star query is usable outside MCP; (b) a digest-drift gate that consumes the affects closure to FAIL when a changed symbol's dependent docs/code were not updated in the same change -- the enforcement half of the north-star (CLAUDE.md: 'a graph of WHAT DOCUMENTATION and WHAT OTHER CODE needs to be updated whenever something is touched'). Cut work must live in tickets, not prose -- this is that ticket.