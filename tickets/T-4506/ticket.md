---
id: T-4506
title: C# end-to-end adapter parity (capability resolver, directive DSL, docs/xref/perf,
  dup/docblock fixture)
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-3232
- T-3856
parent: T-4513
tier: story
sprint: null
runs_last: false
milestone: 0.533.0
flavour: quality_objective
due: null
rank: null
points: 1
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4506
branch: t-4506
scope:
- src/frob/vet/_capability_csharp.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: points
  old_value: null
  new_value: '1'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
- field: flavour
  old_value: null
  new_value: quality_objective
  reason: 'E2 (T-5766): census-based flavour classification (heuristic per E1''s own
    candidate signal)'
  actor: logan
  at: '2026-09-24'
evidence:
- tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_var_local_type_carries_into_a_later_instance_call
- tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_slash_doc_directive_binds
- tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_xml_doc_todo_free_text_note_is_accepted
- tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_xml_doc_waive_directive_on_class_binds
- tests/unit/test_xref.py::test_csharp_finds_property_definition
- tests/unit/test_xref.py::test_csharp_finds_const_field_definition
- tests/unit/test_xref.py::test_csharp_finds_nested_type_definition
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: bring C# to the same adapter contract as python/rust/typescript/kotlin/c (mirrors T-1597's non-negotiable bar). Parent for the leaf tickets under it. blocked_by T-3232/T-3234/T-3856 because each is a generic cross-language bug this story's csharp-specific leaves build on top of -- fixing them here would duplicate those tickets, not extend them.

GIVEN a repo with .cs files using capability-relevant APIs, WHEN frob vet runs, THEN it reports the same capability findings a resolver-backed language reports (not just raw needle matches).
GIVEN a .cs file with // frob:doc, // frob:tests, and // frob:todo T-#### directives, WHEN the graph DSL parser runs, THEN each directive is accepted and produces the same obligation-graph edges Python's # directives produce.
GIVEN the frob.docs/frob.xref/frob.perf gaps fixed by T-3232/T-3234/T-3856, WHEN a csharp file is docstring-extracted, xref --lang filtered, or perf hot-graph collected, THEN csharp participates identically to python.

## Unblock log
- 2026-09-16: unblocked by T-3234 -- same: perf coverage deferred with T-3234