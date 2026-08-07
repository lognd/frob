---
id: T-0423
title: 'compute-once contract: run-scoped memoization for the heavy pure analyses
  (parse/build_graph/analyze_project/find_duplicates)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0418
tier: ticket
sprint: null
scope:
- src/frob/lang/
- src/frob/graph/
- src/frob/arch/
- src/frob/strata/
- src/frob/vet/
- src/frob/check/
- docs/commands/check.md
- tests/unit/test_memo.py
- pyproject.toml
- CHANGELOG.md
- frob.lock
- uv.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/commands/check.md
  reason: T-0423's new public symbols/version bump require doc anchor + test file
    + release bookkeeping edits outside the original src-only scope glob; frob.lock/uv.lock
    touched only as a mechanical side-effect of frob ack / native rebuild
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/test_memo.py
  reason: T-0423's new public symbols/version bump require doc anchor + test file
    + release bookkeeping edits outside the original src-only scope glob; frob.lock/uv.lock
    touched only as a mechanical side-effect of frob ack / native rebuild
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: T-0423's new public symbols/version bump require doc anchor + test file
    + release bookkeeping edits outside the original src-only scope glob; frob.lock/uv.lock
    touched only as a mechanical side-effect of frob ack / native rebuild
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: T-0423's new public symbols/version bump require doc anchor + test file
    + release bookkeeping edits outside the original src-only scope glob; frob.lock/uv.lock
    touched only as a mechanical side-effect of frob ack / native rebuild
  actor: logan
  at: '2026-07-21'
- op: add
  glob: frob.lock
  reason: T-0423's new public symbols/version bump require doc anchor + test file
    + release bookkeeping edits outside the original src-only scope glob; frob.lock/uv.lock
    touched only as a mechanical side-effect of frob ack / native rebuild
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: T-0423's new public symbols/version bump require doc anchor + test file
    + release bookkeeping edits outside the original src-only scope glob; frob.lock/uv.lock
    touched only as a mechanical side-effect of frob ack / native rebuild
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/test_memo.py::test_second_call_with_same_args_is_memo_hit
- tests/unit/test_memo.py::test_different_args_are_distinct_cache_entries
- tests/unit/test_memo.py::test_scope_exit_does_not_leak_across_scopes
- tests/unit/test_memo.py::test_kwargs_are_part_of_the_cache_key
- tests/unit/test_memo.py::test_build_graph_second_call_is_memo_hit
- tests/unit/test_memo.py::test_build_graph_outside_scope_is_never_cached
- tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope
- tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit
- tests/unit/test_memo.py::test_run_memo_scope_nests_without_truncating_outer
- tests/unit/test_memo.py::test_analyze_project_second_call_is_memo_hit
designated_repro_test: null
threat: null
component: null
---
The general fix for "same expensive computation runs across stages" (of which the T-0418 arch double-run is one instance). Rather than annotate-and-statically-detect (declared idempotency -- brittle + naggy), generalize the T-0414 parse-cache pattern: a run-scoped, content/input-keyed memo on the ~5 heavy PURE analyses -- frob.lang parse (done, T-0414), build_graph, analyze_project, find_duplicates -- so a second call within one frob check is a cache HIT, not a re-run. One decorator per function, reset once per invocation (like the parse cache). This makes cross-stage duplication FREE instead of forbidden, with near-zero annotation burden and no false positives. Complement (proper long-term shape, folds into T-0177 daemon): the check orchestrator computes each heavy analysis ONCE and injects the result into every consumer stage (arch advisory + ARCH001 gate share one result object) -- explicit data flow. Acceptance: analyze_project/find_duplicates/build_graph each run at most once per frob check (a call-counter test); frob check output byte-identical; measurable wall-time drop. Keyed on input+content so correctness is preserved (a stale cached result is a correctness bug -- the T-0414 review standard applies).