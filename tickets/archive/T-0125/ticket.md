---
id: T-0125
title: frob.logging.quiet_stdout_logs is not thread-safe; races across concurrent
  frob.arch/frob.dup calls
state: done
kind: bug
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/logging/quiet.py
- src/frob/arch/__init__.py
- src/frob/dup/_legacy.py
- src/frob/app/check_runner.py
- src/frob/app/perf_runner.py
- tests/unit/test_logging_quiet.py
- tests/unit/test_check.py
- tests/unit/test_logging_module.py
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_interleaved_enter_exit_across_threads_never_sticks
- tests/unit/test_logging_quiet.py::TestQuietStdoutLogsReentrance::test_nested_calls_restore_after_outermost_exits
designated_repro_test: null
threat: null
component: null
---
Found while fixing T-0122 (frob check swallowing its final summary, exit 0, no output at all -- the vacuous-pass class T-0102 targets). Root cause: frob.logging.quiet.quiet_stdout_logs() (and its check_runner.py duplicate _quiet_stdout_logs) saves the shared, process-global root logger's stdout StreamHandler level, sets it to WARNING, then restores the SAVED level in a finally block. frob.arch.analyze_project (arch/__init__.py:169) and frob.dup._legacy.find_duplicates (dup/_legacy.py:275) both call this UNCONDITIONALLY (not gated on a --json flag, unlike the map/outline/xref/check runners which only quiet when the caller wants machine-readable stdout). When frob.check's _collect_results runs the arch and dup check stages concurrently in the same ThreadPoolExecutor (src/frob/check/__init__.py), two threads can race quiet_stdout_logs' unguarded save/restore: if thread B enters after thread A has already flipped the handler to WARNING, B's 'saved' value IS WARNING, and B's restore leaves the handler stuck at WARNING even after both threads return cleanly (no exception, no trace). Any INFO-level log call made by the caller afterward (e.g. frob.app.check_runner.run's final _log.info(result.as_text())) is then silently swallowed -- reproduced deterministically: 'uv run frob check' with no --json exited 0 with ZERO printed output in 4 of 5 runs under this repo's own tree. T-0122 mitigated the SYMPTOM from src/frob/check/__init__.py (save/restore the stdout handler level around the whole ThreadPoolExecutor batch in _collect_results, since check/** was T-0122's only declared scope) but did not fix the root cause, which lives in frob.logging/frob.arch/frob.dup -- out of T-0122's scope. Any OTHER caller that runs two of {analyze_project, find_duplicates, quiet_stdout_logs-users} concurrently (outside frob.check, e.g. a custom script or MCP tool composing frob.arch + frob.dup in threads) still has this bug. Fix direction: make quiet_stdout_logs reentrant/thread-safe (e.g. a module-level threading.Lock plus a depth counter so only the outermost caller restores the level, or switch to a per-thread/contextvars-scoped filter instead of mutating the shared handler's level at all).
## Done report

Root fix: quiet_stdout_logs now uses a module-level threading.Lock plus
a reentrancy depth counter -- only the outermost caller across all
threads saves handler levels on entry and restores them at true
outermost exit (depth 0), so the stale-restore interleave cannot stick
the handler at WARNING. Lock held only for bookkeeping, never across
the body (same-thread nesting cannot deadlock); try/finally unwinds
depth on exceptions. The duplicate _quiet_stdout_logs in
app/check_runner.py was removed and callers (check_runner, perf_runner)
route through the canonical frob.logging implementation; T-0122's
check-layer force-restore stays as defense in depth. Reviewer traced
the interleave by hand, confirmed the deterministic regression test
fails on pre-fix code (handler stuck at WARNING), audited both new
PERF003 waives as genuine coarse-heuristic false positives, and
APPROVED. Verified at merge on main: 42 tests across quiet/check
suites green after resolving the T-0107 stamp-baseline conflict.