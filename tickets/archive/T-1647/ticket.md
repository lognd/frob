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
scope:
- src/frob/perf/**
- src/frob/**
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
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
---
T-1204 closed having fixed the PERF010 family (a genuine rule false positive plus four real call sites moved onto the new shared src/frob/yaml_io.py). Its Done report honestly disclosed that the other PERF rules were not attempted. That remainder was never filed, so closing T-1204 dropped it from the queue -- 47 warnings with no owner.

Current unwaived breakdown on main:
- PERF011 x62
- PERF014 x18
- PERF008 x9
- PERF005 x6
- PERF013 x2

Method, per this repo's standing rule (memory: "perf findings become lint rules"): a perf root cause ships as BOTH the fix AND a detector that prevents its return -- a .strata obligation plus a PERF00x rule -- not just the fix. Where a fix reveals a general pattern, propose the rule.

Before fixing anything, classify each rule the way T-1636 and T-1204 both did to good effect: is this real debt, or is the detector firing on a shape its author did not anticipate? T-1204 found exactly the latter in PERF010 -- the detector could not see a C loader selected through a helper call, so the repo's own optimisation read as absent. A rule-level fix that honestly clears 60 findings beats 60 site edits, and PERF011 at 62 findings is the obvious candidate to check first.

MEASUREMENT WARNING, non-negotiable: the perf gate silently under-reports when native extensions are stale. A worktree with unbuilt natives reports zero PERF findings while looking perfectly healthy, and that exact failure deleted 55 live waivers earlier in this drive. Confirm natives are healthy before trusting ANY perf measurement, and measure unscoped -- a --ticket-scoped zero is not a package zero.