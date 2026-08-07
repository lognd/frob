---
id: T-1227
title: frob:enumerates directive + DOCENUM001 -- AST-diff doc-claimed collection members
  vs actual
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1226
tier: ticket
sprint: null
scope:
- src/frob/graph/**
- src/frob/gates/**
- docs/**
- design/frob.strata
- tests/test_docenum_gate.py
- tests/test_graph.py
- tests/unit/graph/test_dsl.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001 fix: docenum001_gate + TestDocenum001Gate need interface declarations
    in design/frob.strata to match the code this ticket added

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_docenum_gate.py
  reason: 'regression corpus tests for frob:enumerates/DOCENUM001

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/test_graph.py
  reason: 'regression corpus tests for frob:enumerates/DOCENUM001

    '
  actor: logan
  at: '2026-07-29'
- op: add
  glob: tests/unit/graph/test_dsl.py
  reason: 'regression corpus tests for frob:enumerates/DOCENUM001

    '
  actor: logan
  at: '2026-07-29'
evidence:
- tests/test_docenum_gate.py::TestDocenum001Gate::test_stale_claimed_list_fires
- tests/test_docenum_gate.py::TestDocenum001Gate::test_corrected_claimed_list_passes
- tests/test_docenum_gate.py::TestDocenum001Gate::test_stale_extra_claimed_member_fires
- tests/test_docenum_gate.py::TestDocenum001Gate::test_strenum_members_extracted
- tests/test_docenum_gate.py::TestDocenum001Gate::test_malformed_target_shape_fires
- tests/test_docenum_gate.py::TestDocenum001Gate::test_unresolvable_shape_is_disclosed_not_silently_passed
- tests/test_graph.py::TestDsl::test_enumerates_verb_binds_bare_doc_anchor_target
- tests/test_graph.py::TestMarkdownAnchors::test_enumerates_edge_carries_claimed_members
designated_repro_test: null
threat: null
component: null
---
Doc span binds to a named collection literal (dict/set/tuple/Literal/ErrorSet/StrEnum); gate AST-diffs claimed members vs actual at check time, independent of ack state. Acceptance: fires on the two known-stale check.md _STAGE_GROUPS tables pre-fix (regression corpus); the sweep's drift-lock candidate list (docs/audits/docs-staleness-2026-07-29.md, 'Drift-lock candidates' section) gets bound as the initial adoption wave. Ref: gate-gap class 1 in docs/audits/docs-staleness-2026-07-29.md.