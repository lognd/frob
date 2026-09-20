---
id: T-3788
title: fix win32 EffectGraph symref path-separator mismatch
state: done
kind: bug
origin: human
created: '2026-09-04'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/_effect_summaries.py tests/unit/perf/test_effect_summaries.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 waiver: win32-only defect, cannot repro on Linux CI'
  actor: logan
  at: '2026-09-04'
  old_length: 200
  new_length: 857
evidence:
- tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_ambiguous_cross_file_callee_yields_an_explicit_unknown_member
- tests/unit/perf/test_effect_summaries.py::TestEffectGraphSummaryUnknownDegradation::test_fully_resolvable_call_path_has_no_unknown_member
- tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_splat_argument_nested_in_a_literal_yields_an_unknown_member
- tests/unit/perf/test_effect_summaries.py::TestSplatArgumentDegradesToUnknown::test_plain_named_parameter_forward_is_not_treated_as_a_splat
- tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_lru_cache_decorated_symbol_is_memoized
- tests/unit/perf/test_effect_summaries.py::TestMemoizedCalleeDetection::test_functools_dotted_lru_cache_decorator_is_memoized
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
win32 CI: 6 tests in tests/unit/perf/test_effect_summaries.py fail. Investigation TBD via winrun traceback. Likely same path-separator symref-mismatch pattern as T-3784/T-3786. Part of win32 CI drain.

frob:waive BUG002 reason="win32-only defect confirmed via winrun; the bound tests build symrefs directly from str(Path) instead of ParsedFile.path (a POSIX-normalized display path via _display_path/.as_posix()) -- on Linux str(Path) is already POSIX-separated so the pre-fix test also passed at the parent commit, but on win32 str(Path) is backslash-separated and mismatched EffectGraph's internal POSIX symref keys, causing every summary()/is_memoized() lookup to return empty. Fixed by building test symrefs from parsed.path instead of the raw filesystem path. No Linux-repro-at-parent-commit test can demonstrate a win32-only path-separator mismatch."