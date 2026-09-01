---
id: T-3595
title: Split tests/unit/test_rapid_sweep.py (5055 lines) into a per-gate-family package,
  reusing T-3586's recipe
state: in-progress
kind: feature
origin: agent
created: '2026-08-31'
priority: medium
blocked_by:
- T-3586
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_rapid_sweep.py
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/integration/test_gitlog.py
  reason: 'SCOPE002: these files exercise conftest.py fixtures/hooks (run_bounded_subprocess,
    pytest_configure, pytest_collection_modifyitems, pytest_sessionfinish, _reset_parse_cache_before_test,
    _stall_detected) already covered by this ticket''s declared tests/conftest.py
    scope -- declaring coverage, not new code touch'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/test_mutate_journal.py
  reason: 'SCOPE002: these files exercise conftest.py fixtures/hooks (run_bounded_subprocess,
    pytest_configure, pytest_collection_modifyitems, pytest_sessionfinish, _reset_parse_cache_before_test,
    _stall_detected) already covered by this ticket''s declared tests/conftest.py
    scope -- declaring coverage, not new code touch'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_conftest_parse_reset.py
  reason: 'SCOPE002: these files exercise conftest.py fixtures/hooks (run_bounded_subprocess,
    pytest_configure, pytest_collection_modifyitems, pytest_sessionfinish, _reset_parse_cache_before_test,
    _stall_detected) already covered by this ticket''s declared tests/conftest.py
    scope -- declaring coverage, not new code touch'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_conftest_stackdump.py
  reason: 'SCOPE002: these files exercise conftest.py fixtures/hooks (run_bounded_subprocess,
    pytest_configure, pytest_collection_modifyitems, pytest_sessionfinish, _reset_parse_cache_before_test,
    _stall_detected) already covered by this ticket''s declared tests/conftest.py
    scope -- declaring coverage, not new code touch'
  actor: logan
  at: '2026-09-01'
- op: add
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: 'SCOPE002: these files exercise conftest.py fixtures/hooks (run_bounded_subprocess,
    pytest_configure, pytest_collection_modifyitems, pytest_sessionfinish, _reset_parse_cache_before_test,
    _stall_detected) already covered by this ticket''s declared tests/conftest.py
    scope -- declaring coverage, not new code touch'
  actor: logan
  at: '2026-09-01'
- op: remove
  glob: tests/integration/test_gitlog.py
  reason: revert speculative scope-closure additions -- SCOPE002 cascades transitively
    through tests/conftest.py's full pre-existing coverage graph regardless of this
    split's actual diff; out of scope for T-3595, filing separately if it blocks land
  actor: logan
  at: '2026-09-01'
- op: remove
  glob: tests/test_mutate_journal.py
  reason: revert speculative scope-closure additions -- SCOPE002 cascades transitively
    through tests/conftest.py's full pre-existing coverage graph regardless of this
    split's actual diff; out of scope for T-3595, filing separately if it blocks land
  actor: logan
  at: '2026-09-01'
- op: remove
  glob: tests/unit/test_conftest_parse_reset.py
  reason: revert speculative scope-closure additions -- SCOPE002 cascades transitively
    through tests/conftest.py's full pre-existing coverage graph regardless of this
    split's actual diff; out of scope for T-3595, filing separately if it blocks land
  actor: logan
  at: '2026-09-01'
- op: remove
  glob: tests/unit/test_conftest_stackdump.py
  reason: revert speculative scope-closure additions -- SCOPE002 cascades transitively
    through tests/conftest.py's full pre-existing coverage graph regardless of this
    split's actual diff; out of scope for T-3595, filing separately if it blocks land
  actor: logan
  at: '2026-09-01'
- op: remove
  glob: tests/unit/test_conftest_suite_result_status.py
  reason: revert speculative scope-closure additions -- SCOPE002 cascades transitively
    through tests/conftest.py's full pre-existing coverage graph regardless of this
    split's actual diff; out of scope for T-3595, filing separately if it blocks land
  actor: logan
  at: '2026-09-01'
evidence:
- tests/unit/rapid_sweep_suite/test_baseline.py::TestRollingBaseline::test_write_then_read_round_trips
- tests/unit/rapid_sweep_suite/test_sweep_run.py::TestDeferredSweepRun::test_unmeasurable_check_leaves_the_baseline_untouched
- tests/unit/rapid_sweep_suite/test_commit.py::TestCommitRapidDebt::test_leaves_the_repo_clean
- tests/unit/rapid_sweep_suite/test_attribution.py::TestAttributeNewFindings::test_empty_queue_returns_empty_mapping
- tests/unit/rapid_sweep_suite/test_filing.py::TestRelativizeRegressionScopeFile::test_absolute_under_root_is_relativized
- tests/unit/rapid_sweep_suite/test_dispose.py::TestAutoDisposeFiledFindings::test_disposes_findings_the_ticket_covers
- tests/unit/rapid_sweep_suite/test_worktrees.py::TestSweepStaleWorktreesAfterLand::test_never_uses_force
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Sibling split to T-3586 (which owns tests/test_gates.py, 21691 lines,
the FIRST split and the recipe owner). This ticket owns ONE of the five
other monofile test suites named in T-3586's MEASURED wc -l list:

    12596 tests/test_ticket_land.py
     8910 tests/unit/test_arch.py
     7992 tests/test_vet.py
     5935 tests/unit/test_coordinator_scripts.py
     5055 tests/unit/test_rapid_sweep.py

RECIPE (established by T-3586, T-3587):

1. `frob refactor split`/`move`/`move-module` needed T-3587 first
   (landed: module_to_path hardcoded src/ as the sole package root, so
   the verbs could not address any tests/** module at all -- fixed via
   a shared import_roots/root_for_path root list). Confirm the T-3587
   fix is on `main` before starting -- `uv run frob refactor split
   tests.<this-file-without-py> --symbols X --into tests.gates_suite.x`
   (or your own destination package name) should resolve without a
   "module file missing: .../src/tests/..." error.

2. Cluster this file's test classes by family (section comments/class
   names make this mechanical) into one module per family under a new
   sibling package, using `frob refactor split --skip-check-delta`
   (`frob check --delta`'s own 100s budget is exceeded by this repo's
   size regardless of diff size -- a pre-existing infra cost, not a
   split defect; verify with your own scoped `frob check` instead,
   never skip verification, just don't rely on split's internal
   check_delta post-condition).

3. AFTER each split, the re-export shim `split` leaves in the source
   module (`from DEST import (...)  # noqa: F401`) causes pytest to
   DOUBLE-COLLECT every moved test class -- pytest gathers any
   `Test*`-named object visible in a module's namespace, imported or
   locally defined, not just AST-defined-there. Remove the shim block
   after confirming (via `git diff`) every repo-local frob:tests/
   evidence reference was already rewritten by the split's own
   transaction (it always is -- that IS the transaction's job); then
   re-verify collection count with `pytest <both files>
   --collect-only -q` and confirm it matches the pre-split total
   exactly.

4. `frob refactor move` (unlike `split`, T-3122) does NOT carry
   forward imports a moved symbol's body or default-argument
   expressions need, and neither `move` nor `split` patches OTHER
   files' (including the source module's own remaining classes', or a
   freshly split-out destination module's) bare-name references to a
   symbol that moved out from under them -- only explicit `from X
   import symbol` statements get rewritten. Any shared test helper
   (`_write`, `_snapshot`, fixture-style functions, etc.) used across
   multiple families needs: (a) `frob refactor move
   tests.<file>:_helper tests.conftest:_helper` for each one,
   one at a time (its own module-import verify step will surface any
   missing carried-forward import -- add the single missing import
   line by hand, confirmed minimal); (b) a manual `from tests.conftest
   import (...)` block added to every surviving file that references
   the helper as a bare name (the source file and any split
   destination files) -- this is fixing a documented tool gap, not a
   hand-move of test logic; never author new test bodies by hand.

5. A module-level CONSTANT (e.g. a string/tuple fixture literal) used
   across families cannot be moved by `move`/`split` at all -- v1 scope
   is function/class defs only (`frob.refactor._resolve.resolve_symbol`'s
   own docstring). Relocate these by hand into tests/conftest.py (or
   this ticket's own shared module) for the same reason as (4b).

6. Preserve markers: `xdist_group`/`timeout`/T-2099's
   heavy_subprocess-by-MODULE grouping -- moving a class to a new
   module changes its T-2099 group key; note the effect on
   parallel/peak-memory behavior for any class carrying that marker.

7. Prove closure per batch: `frob check --only gates-fast --budget 300
   --ticket <this-id>` before landing, plus the moved+source files'
   own pytest run at 100% green with the exact pre-split collection
   count.

ACCEPTANCE: this file either deleted or reduced to a thin re-export
shim under 200 lines (state which and why, matching T-3586's own
precedent); zero new gate errors; collection count preserved exactly.
