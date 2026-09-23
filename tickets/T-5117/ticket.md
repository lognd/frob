---
id: T-5117
title: over_broad_literal_globs/declared_source_prefixes uncached per ticket-holder
  pair (TICK008 third bottleneck)
state: done
kind: bug
origin: human
created: '2026-09-19'
priority: medium
blocked_by:
- T-4722
- T-4767
parent: T-4806
tier: ticket
sprint: null
runs_last: false
milestone: 0.533.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_models.py
- src/frob/lang/_nodes.py
- tests/unit/test_pyproject_data_memoization.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_pyproject_data_memoization.py
  reason: T-5117 needs a repro test for the over_broad_literal_globs/declared_source_prefixes
    uncached-per-pair regression (BUG002 evidence requirement)
  actor: logan
  at: '2026-09-20'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_derives_package_prefix_for_a_differently_named_project
- tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_this_repos_own_src_frob_globs_are_unchanged
- tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_scales_across_many_candidates_and_leases
- tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_declared_source_prefixes_resolve_calls_stay_o1_across_pairs
designated_repro_test: tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_declared_source_prefixes_resolve_calls_stay_o1_across_pairs
acceptance:
- text: test_real_repo_ledger_is_tick008_clean completes well within its Windows CI
    timeout with T-5036 and T-5075 also applied
  evidence:
  - tests/test_tickets_lease.py::TestOverBroadLiteralGlobs::test_derives_package_prefix_for_a_differently_named_project
  - tests/unit/test_pyproject_data_memoization.py::TestPyprojectDataMemo::test_declared_source_prefixes_resolve_calls_stay_o1_across_pairs
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Follow-up to T-5036 (repo_root memoization) and T-5075 (leases snapshot threading): with BOTH fixes applied, tests/gates_suite/test_tick.py TestTick008UnknownLedgerFields test_real_repo_ledger_is_tick008_clean STILL stalls (reproduced both locally on Linux, single-worker, and via winrun on Windows with faulthandler). New faulthandler dump shows a THIRD, previously-undiscovered bottleneck: doable() -> leased_by() -> _leased_by_one_holder() -> over_broad_literal_globs(root) (src/frob/tickets/_models.py) -> declared_source_prefixes(root) (src/frob/lang/_nodes.py) -> Path.resolve() -- same failure shape as T-5036's repo_root and T-5075's read_all_leases: an expensive, uncached-per-call operation invoked once per (ticket, holder) pair despite _leased_by_one_holder already receiving a precomputed breadth tuple (the T-0453 pattern), because over_broad_literal_globs(root) itself is called fresh inside the per-pair branch rather than being threaded in as part of that precomputed breadth. Fix direction: thread a precomputed literal_globs value into breadth (or a new parameter alongside it) the same way doable()/leased_by already thread breadth and worktree_leases, computed once per doable() invocation instead of once per pair. Verify via winrun with faulthandler after the fix, same recipe T-5036/T-5075 used.