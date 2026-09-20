---
id: T-1647
title: 'PERF remainder: PERF011/014/008/005/013 that T-1204 disclosed but did not
  attempt'
state: done
kind: feature
origin: human
created: '2026-08-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/perf/**
- src/frob/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense PERF011 repo-scan-iterable fix history into T-1647 body
  actor: logan
  at: '2026-09-19'
  old_length: 1617
  new_length: 2520
evidence:
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_the_loops_own_iterable
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_earlier_loop_is_an_unrelated_genexpr
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_when_scan_is_a_nested_loops_own_iterable
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_fires_on_pre_fix_shape
- tests/unit/perf/test_hotpath_smells.py::TestPerf011RepoScanInLoop::test_does_not_fire_when_scan_is_hoisted
- tests/test_cache_gate.py::TestMemoizedReadCoverage::test_uncovered_read_fires
- tests/test_cache_gate.py::TestT1454RegressionShape::test_env_read_fires
- tests/test_serve_watch.py::TestWatchTick::test_watch_tick_never_disagrees_with_pull_signal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-1204 closed having fixed the PERF010 family (a genuine rule false positive plus four real call sites moved onto the new shared src/frob/yamlio.py). Its Done report honestly disclosed that the other PERF rules were not attempted. That remainder was never filed, so closing T-1204 dropped it from the queue -- 47 warnings with no owner.

Current unwaived breakdown on main:
- PERF011 x62
- PERF014 x18
- PERF008 x9
- PERF005 x6
- PERF013 x2

Method, per this repo's standing rule (memory: "perf findings become lint rules"): a perf root cause ships as BOTH the fix AND a detector that prevents its return -- a .strata obligation plus a PERF00x rule -- not just the fix. Where a fix reveals a general pattern, propose the rule.

Before fixing anything, classify each rule the way T-1636 and T-1204 both did to good effect: is this real debt, or is the detector firing on a shape its author did not anticipate? T-1204 found exactly the latter in PERF010 -- the detector could not see a C loader selected through a helper call, so the repo's own optimisation read as absent. A rule-level fix that honestly clears 60 findings beats 60 site edits, and PERF011 at 62 findings is the obvious candidate to check first.

MEASUREMENT WARNING, non-negotiable: the perf gate silently under-reports when native extensions are stale. A worktree with unbuilt natives reports zero PERF findings while looking perfectly healthy, and that exact failure deleted 55 live waivers earlier in this drive. Confirm natives are healthy before trusting ANY perf measurement, and measure unscoped -- a --ticket-scoped zero is not a package zero.

<!-- narrative-moved:src/frob/perf/_hotpath_smells.py:193:T-1647 -->
T-1647: PERF011 used to flag a repo-scan call the instant ANY for/while
token appeared earlier in the flattened stream. An audit of every live
PERF011 finding on main found this systematically misfired on
`for x in <repo-scan-call>(...):` and its comprehension/genexpr
equivalents -- that call is the loop's own ITERABLE expression,
evaluated exactly ONCE to build the iterator, never "once per
iteration" the way the mined T-1207 shape (a call inside the loop
BODY) is. 22 of 31 findings were exactly this shape, including one
where the "earlier loop" was an unrelated genexpr's own for-clause
with no relation to the later, un-looped call it caused to misfire.
See `_perf011_repo_scan_in_loop`'s own docstring below for the fix and
its one disclosed residual gap (sibling, not nested, loops).
frob:ticket T-1225
frob:ticket T-1647