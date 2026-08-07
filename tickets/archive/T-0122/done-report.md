## Done report

Swallowed-summary mechanism traced: quiet_stdout_logs() saves the
process-global root logger stdout handler level, forces WARNING, and
restores the SAVED value; arch.analyze_project and dup._legacy.
find_duplicates call it unconditionally, and check's _collect_results
runs those stages concurrently in one ThreadPoolExecutor, so the losing
thread saves WARNING and its restore leaves the handler stuck -- the
final _log.info(result.as_text()) is then dropped while exiting 0
(reproduced 4/5 pre-fix; the installed pre-fix global binary reproduced
it live during the merge as well).

The ticket's original double-build hypothesis is obsolete: arch was
decoupled from frob.graph by T-0043; build_graph runs exactly once per
check invocation, now locked by a counting regression test.

Fix: _collect_results saves stdout handler levels before the executor
batch and force-restores them in a finally (helpers
_run_tasks_concurrently + _restore_stdout_log_levels). Root
thread-unsafety of quiet_stdout_logs itself is tracked as T-0125
(logging/arch/dup scope, outside this ticket).

Verification (reviewer-confirmed): deterministic regression test fails
on pre-fix code (30 == 10) and passes post-fix; frob check looped with
summary present every run, exit 0; gates JSON stable A-B; scope clean
(check/__init__.py, tests/unit/test_check.py, tickets.md only).
