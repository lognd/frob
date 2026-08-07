## Done report

Investigated the crash mechanism rather than reaching for serialization first,
per the ticket's own instruction.

.frob/last-coverage-run.log (the same log T-1416's brief cites) records the
exact incident: worker gw0 hard-crashed ("[gw0] node down: Not properly
terminated") immediately after test_check_unaffected_when_no_strata_files
(the T-1416 cache-recreate defect, already fixed and landed separately),
while queued to run tests/system/test_frob_self_model.py::TestFrobSelfModel
::test_sys_gate_zero_violations. No traceback because the worker process
itself died, not a caught exception inside a test.

tickets.md already contains a prior investigation of this exact incident
under T-1385 ("Logging handler holds a stale captured sys.stderr, polluting
stderr assertions and crashing xdist workers", state: done, landed to main
before this worktree's base). T-1385's Done report documents "Symptom B" as
the identical crash: repeated 'ValueError: I/O operation on closed file'
from logging/__init__.py's emit(), immediately before '[gw0] node down: Not
properly terminated' while running this exact test
(test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations).

Root cause (per T-1385, confirmed applicable here): frob.logging.logger's
dictConfig binds its StreamHandler to whichever object sys.stdout/sys.stderr
happens to be at the FIRST get_logger() call in a process -- under a
full-suite xdist run, frequently a pytest capsys/capfd substitute stream
belonging to whatever test happened to trigger the first-ever log call. Once
that substitute stream's owning test tears down and closes it, every later
Handler.emit() in that worker process raises ValueError: I/O operation on
closed file. logging.Handler.handleError reports this via
"--- Logging error ---", repeated enough times under xdist's sustained
logging traffic (sys_gate + build_graph over the FULL self-model graph
produce sustained logging.warning() traffic) that the worker process itself
dies -- not a Python exception inside the test, hence no traceback captured
by pytest.

T-1385 landed the fix (src/frob/logging/handler.py: _LazyStdoutHandler/
_LazyStderrHandler, StreamHandler subclasses whose `stream` property
re-resolves sys.stdout/sys.stderr on every access instead of caching the
object seen at bind time) before this ticket's worktree base -- it is
already on main, not something T-1240 needs to (re)implement. This ticket's
own declared scope (src/frob/gates/_sys.py, src/frob/strata/**) contains no
code implicated in the crash: the fault was in the logging handler binding,
not in the SYS gate or strata self-model logic itself -- the SYS gate test
was simply the heaviest, most log-traffic-generating test in the suite,
which is why it was the one that hit the race.

Verified the fix holds under repeated parallel reproduction attempts (no
crash across 6 separate runs total):
- The coordinator's exact repro command (test_cli_native_missing.py +
  test_frob_self_model.py under -n 4): 7 passed, 34s -- no worker crash.
- test_frob_self_model.py alone under -n 4, 3 separate runs: 4 passed each
  time (46-79s), no worker crash, no "node down".
- test_frob_self_model.py + test_cli_native_missing.py +
  test_main_entry.py (T-1385's own regression tests) together under -n 6,
  2 separate runs: 20 passed each time (~31s), no worker crash.

No code change was made under this ticket's scope: the crash's actual
mechanism lives in src/frob/logging/handler.py, outside T-1240's declared
scope, and was already fixed and landed by T-1385 before this
investigation began. Regression coverage for the causal mechanism already
exists and is bound as evidence here: T-1385's TestLazyLogHandlers tests
directly exercise "a handler must never emit against a stream captured at
bind time, only the current one" -- the exact defect class that crashed
gw0. Adding a second test asserting the identical mechanism inside T-1240's
own scope would duplicate that coverage, not add anything a revert of
T-1385's fix wouldn't already be caught by.

### Changed
```
 tickets.md | 14 +++++++++++---
 1 file changed, 11 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestLazyLogHandlers::test_stderr_handler_never_emits_against_a_closed_captured_stream` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stderr]` (pytest node id, verified passing when recorded)
- `tests/unit/test_main_entry.py::TestLazyLogHandlers::test_handler_follows_stream_swap_not_bind_time_capture[stdout]` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4859 warning(s), 697 waived
- error-findings: none (measured, zero errors)
