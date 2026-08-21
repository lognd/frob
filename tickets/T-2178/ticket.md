---
id: T-2178
title: 'DEPR call-detection is a self-admitted textual heuristic, not a parse: _looks_like_call
  regexes raw source lines, so a commented-out mention counts as a live call and an
  aliased call is missed'
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: T-1662
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_debt_deprecated.py
evidence_scope:
- tests/unit/gates/test_deprecated_baseline.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_non_call_mention_with_trailing_comment_call_shape_is_not_a_call
- tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_call_through_import_alias_is_reported
designated_repro_test: tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_non_call_mention_with_trailing_comment_call_shape_is_not_a_call
acceptance:
- text: The fix MUST decide from tokens/grammar, never text. Resolve 'is this deprecated
    symbol called here' from the parsed AST (a real ast.Call whose func resolves to
    the symbol) and/or frob.graph's import+call edges, exactly as REF001 was fixed
    under T-1665. Do NOT strip comments and keep regexing -- that patches one direction
    and leaves aliased and attribute calls wrong. This test MUST fail against current
    main.
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_unrelated_same_name_call_in_non_importing_file_is_excluded
- text: Given a file whose ONLY mention of a deprecated symbol is inside a comment
    or string literal, when the DEPR gate runs, then it reports no call site (today
    _looks_like_call matches it -- src/frob/gates/_debt_deprecated.py:503, applied
    at :610 to raw (file,line,ctx) text hits with no comment stripping).
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_non_call_mention_with_trailing_comment_call_shape_is_not_a_call
- text: Given a file that imports a deprecated symbol under an alias and calls it
    through that alias, when the DEPR gate runs, then the call IS reported (today
    the bare-name regex cannot see it).
  evidence:
  - tests/unit/gates/test_deprecated_baseline.py::TestDeprecatedCurrentReferencesImportGating::test_call_through_import_alias_is_reported
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: d6d91f5ac217450f0c981c508bb598cc02e2d2f5
---
