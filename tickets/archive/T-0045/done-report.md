## Done report

Baseline (before): src/frob/perf/_heat.py, _profile.py, _rules.py already carried
zero PERF001-004 self-flags and zero arch long-function warnings -- prior work
under T-0021/T-0027 had already split them into small private helpers
(_relativize, _enclosing_symbol, _symbols_by_path, _accumulate_totals,
_build_entries in _heat.py; _artifact_sha, _harness_argv, _run_profiled,
_persist_artifact, _choose_meta_path in _profile.py; _container_kinds,
_container_call_kinds, _for_clause_in_indices, _loop_gate, per-rule helpers,
_python_violations, _best_effort_violations, _symbol_violations in _rules.py).
Verified via `analyze_project(Path('src/frob/perf'))` (0 long-function
suggestions) and `perf_rules(None, files)` over src/frob/perf/*.py (0
violations).

The one real long-function warning inside T-0045's declared scope was
tests/test_perf.py:197 test_heat_joins_pstats_rows_onto_symbol_spans (31
lines, threshold 30). Fixed by extracting the git-init/workload-file setup
into a new private helper `_init_hot_cold_workload(tmp_path)` (module-level,
next to the existing `_write` helper), bringing the test body down.
Behavior preserved exactly -- same subprocess/git-init/write calls, same
assertions.

Reviewer (first pass) correctly REJECTED an earlier version of this report:
that version deferred a PERF001/PERF003 self-flag at
test_heat_joins_pstats_rows_onto_symbol_spans (line 219 after the helper
extraction) to a new ticket T-0121, on the theory it was "pre-existing and
unrelated." The reviewer called this scope avoidance -- tests/test_perf.py
is explicitly in T-0045's scope and the ticket title is literally "clear
PERF-rule self-flags," so an in-scope self-flag is not an out-of-scope
discovery no matter how the code got there. Fixed for real instead: the
test's `[e.ref for e in report.entries]` list comp plus
`next(e for e in report.entries if e.ref == "workload.py::hot")` genexpr
tripped the for_count>=2-plus-== PERF003 heuristic (and the membership-style
PERF001 read). Restructured to a single dict comprehension plus direct
lookup -- `entries_by_ref = {entry.ref: entry for entry in report.entries}`,
then `entries_by_ref["workload.py::hot"]` -- which has one `for` and no
`==`, so it no longer matches either rule's token pattern, and reads at
least as clearly as the original. No frob:waive needed. T-0121 has been
withdrawn (state: dropped) with a reason pointing back here -- see its
entry.

Changed:
- tests/test_perf.py::_init_hot_cold_workload (new private helper)
- tests/test_perf.py::test_heat_joins_pstats_rows_onto_symbol_spans (setup
  extracted into the helper above; entries-lookup restructured from a list
  comp + next(genexpr) pair to a dict comp + direct index, clearing
  PERF001/PERF003; assertions otherwise unchanged)

Evidence:
- `uv run pytest tests/test_perf.py -q` -- 18 passed
- `uv run python -c "from frob.arch import analyze_project; ..."` over
  src/frob/perf and over tests/test_perf.py -- 0 long-function warnings
  (only 2 pre-existing abstraction-opportunity *suggestions* on _rules.py,
  informational/"note" severity, not gating)
- `uv run python -c "from frob.perf._rules import perf_rules; ..."` over
  src/frob/perf/*.py AND over tests/test_perf.py -- 0 violations in both
- `frob check --ticket T-0045 --json --only gates` -- diagnostics are
  exactly: 1x SCOPE001 (tickets.md, ticket-ledger mechanics, expected for
  any ticket that runs `frob ticket new`/`start`), 1x PRE001 (stale
  pre-work sweep, cleared by re-running `frob ticket sweep T-0045`), plus
  repo-wide TEST002/TEST003/TEST006 warnings from unrelated modules
  (strata) that predate this ticket and are out of scope. Zero PERF001-004
  and zero long-function findings anywhere under tests/test_perf.py or
  src/frob/perf/**.
- Repo-wide regression check: `frob check --json --only gates` (no
  --ticket) diagnostic count is 132 on this worktree vs 134 on main
  (measured via `git stash` of tests/test_perf.py + tickets.md then
  re-running the same command) -- 2 fewer, matching the two PERF findings
  cleared on tests/test_perf.py; no new diagnostics introduced anywhere
  else in the repo.

Filed (out-of-scope discoveries, not fixed here):
- T-0119: src/frob/app/perf_runner.py _heat_body (42 lines) / _annotate (33
  lines) trip the long-function bar -- scope is src/frob/app/**, not
  src/frob/perf/**
- T-0120: tests/system/test_cli_perf.py
  TestCheckOnlyPerf.test_perf001_fixture_warns_but_check_exits_zero (38
  lines) trips the long-function bar -- scope is tests/system/**, not
  tests/test_perf.py
- T-0121: dropped (see its entry) -- was an incorrect deferral of an
  in-scope PERF001/PERF003 finding; resolved directly in T-0045 instead.

Gates: frob check --ticket T-0045 clean for src/frob/perf/** and all of
tests/test_perf.py -- zero PERF001-004 self-flags, zero long-function
warnings. The only diagnostics remaining under --ticket are SCOPE001 on
tickets.md (ledger mechanics) and PRE001 (stale-sweep, cleared by
re-sweeping) plus pre-existing out-of-scope strata TEST00x warnings.
Repo-wide gate diagnostic count (132) does not exceed main's baseline
(134). No frob:waive used anywhere in this ticket's scope.
