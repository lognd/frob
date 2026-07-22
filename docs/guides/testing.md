# Testing guide: per-test timeout (CI hardening, T-0692)

## The deadlock class this guards against

`_run_combined_jobs` (the combined-gates path `frob check` and several
`TestRunGatesDelta`-family tests exercise) forks a `ProcessPoolExecutor`
from inside an already-running `ThreadPoolExecutor` (disclosed in T-0265's
Done report). Under specific interleavings this wedges permanently: no
exception, no output, just a process tree that never returns. Locally this
has shown up as zombie `pytest` trees left behind by dead worktree
sessions, still running 10+ hours later. In CI the same class of hang has
no operator watching for a stuck process -- it silently burns the entire
job cap (observed: 5h59m30s before the platform's own 6h ceiling cancelled
the job) and reports nothing more specific than "cancelled", with no
indication of which test wedged.

T-0581 tracks the structural fix (redesigning the combined-jobs path so it
does not nest a process pool inside a thread pool). This ticket (T-0692) is
the harness guard, not the fix: it does not make the deadlock impossible,
it makes a deadlock fail FAST and NAMED, so:

- a hang costs minutes of CI time, not most of a 6h job cap;
- the failure output names the exact test that wedged, instead of an
  undifferentiated job cancellation; and
- a hang in a local dev loop or a dispatched agent's targeted test run
  surfaces the same way, instead of silently spawning a zombie process
  tree that outlives the session.

## The mechanism: pytest-timeout, thread method, 120s default

`pyproject.toml`'s `[tool.pytest.ini_options]` sets:

```
addopts = "-q -n auto --timeout=120 --timeout-method=thread"
```

Every test gets a 120-second ceiling by default. Two things about this are
deliberate, not defaults left untouched:

- **`method=thread`, not the pytest-timeout default (`signal` on
  platforms where it's available).** The signal method relies on the main
  thread receiving and handling `SIGALRM`, which does not fire reliably
  once execution is wedged inside a forked subprocess or blocked deep in a
  native (PyO3) call -- exactly the state this guard exists to catch. The
  thread method runs a separate watchdog thread that raises inside the
  hung test's frame and dumps a full stack trace of exactly where it was
  stuck, independent of whether the main thread can still respond to
  signals. That stack trace is the difference between "some test hung"
  and "here is the exact call site it wedged in."
- **120 seconds, not something tighter.** Short enough that a real
  deadlock reads as a fast, isolated CI failure instead of eating the job
  cap; long enough that it does not false-positive on ordinary
  slower-than-a-unit-test work (native-extension builds already happened
  before pytest starts, so this ceiling only has to cover in-test work).

## Per-test overrides for legitimately slow tests

A 120s global ceiling is a floor for "this is suspiciously long," not a
claim that every real test is fast. Tests that legitimately need more time
must say so explicitly with `@pytest.mark.timeout(N)` on the test (or
`pytestmark = pytest.mark.timeout(N)` at module scope) -- do not raise the
global default to accommodate one slow file, since that dilutes the guard
for everything else.

Known case at the time this guide was written:
`tests/system/test_scaffold_dx.py` is marked `pytest.mark.slow` (spawns a
real `uv sync`, a real venv, and the full lint/typecheck/test/`frob check`
pipeline against a freshly scaffolded project) and legitimately runs well
past 120s. Adding its override (and auditing the rest of `tests/system/**`
for any other file that runs close to or past the ceiling) is out of this
guide's own scope -- it requires editing files under `tests/system/**`,
which T-0692 (config-only: `pyproject.toml`, `Makefile`,
`docs/guides/**`) does not touch. That follow-up is tracked separately
(see the ticket this guide's own history was filed under for the exact
id) rather than folded in silently.

## Verifying the guard locally

A deliberately-hanging test (`time.sleep()` well past the ceiling, or a
test that blocks on an unresolvable lock/queue) should:

1. Fail on its own after ~120s (not the full test-run timeout, not a
   silent hang).
2. Report `Failed: Timeout >120.0s` (pytest-timeout's own failure message)
   attributed to that one test's node id, with a thread stack dump showing
   where it was blocked.
3. Not affect any other test in the same run -- `-n auto` (pytest-xdist)
   isolates each test onto a worker process, so one hung test's timeout
   does not starve or delay its siblings.

Do not commit a hanging test as a permanent fixture; verify with a
throwaway test file, confirm the behavior above, then delete it.
