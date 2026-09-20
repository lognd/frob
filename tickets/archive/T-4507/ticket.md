---
id: T-4507
title: 'C# comment DSL parity: frob:doc/frob:tests/frob:todo in // and ///'
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4506
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/lang/_walk_csharp.py
- src/frob/lang/_extract.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_slash_doc_directive_binds
- tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_xml_doc_todo_free_text_note_is_accepted
- tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_xml_doc_waive_directive_on_class_binds
designated_repro_test: null
acceptance:
- text: 'GIVEN a C# method with ''// frob:doc docs/x.md#anchor'' above it, WHEN the
    graph builds, THEN a doc edge is recorded for that symbol identically to a Python
    # frob:doc edge.'
  evidence:
  - tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_slash_doc_directive_binds
- text: GIVEN a C# method with '/// frob:todo T-#### some free-text note', WHEN DSL001
    parses it, THEN the free-text note is accepted (not rejected as malformed attribute
    syntax).
  evidence:
  - tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_xml_doc_todo_free_text_note_is_accepted
- text: GIVEN a C# class with a frob:waive directive, WHEN frob check runs, THEN the
    waiver is applied and appears in the waiver ledger the same as a Python-sourced
    waiver.
  evidence:
  - tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity::test_xml_doc_waive_directive_on_class_binds
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Verify/extend the directive DSL comment-extraction path so // and /// C# comments carry frob:doc, frob:tests, frob:todo, frob:ticket, frob:waive exactly like Python's # comments, once T-3856's cross-language free-text fix lands. blocked_by T-3856 because its DSL001 hash-tail bug is the generic parser fix this depends on.

GIVEN a C# method with '// frob:doc docs/x.md#anchor' above it, WHEN the graph builds, THEN a doc edge is recorded for that symbol identically to a Python # frob:doc edge.
GIVEN a C# method with '/// frob:todo T-#### some free-text note', WHEN DSL001 parses it, THEN the free-text note is accepted (not rejected as malformed attribute syntax).
GIVEN a C# class with a frob:waive directive, WHEN frob check runs, THEN the waiver is applied and appears in the waiver ledger the same as a Python-sourced waiver.

## Unblock log
- 2026-09-17: unblocked by T-3856 -- T-3856 landed 666c3c196