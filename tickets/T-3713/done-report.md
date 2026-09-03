## Done report

Changed:
src/frob/check/__init__.py::_timing_atexit
src/frob/check/__init__.py::_timing_dump_thread_inventory
src/frob/check/__init__.py::_timing_atexit_print
src/frob/check/__init__.py::_timing_dump_one_thread_stack
tests/unit/test_check_admission.py::TestTimingDebug (frob:ticket edge added)
tests/unit/test_check_admission.py::TestTimingDebug.test_thread_inventory_silent_when_disabled
tests/unit/test_check_admission.py::TestTimingDebug.test_thread_inventory_lists_every_live_thread
tests/unit/test_check_admission.py::TestTimingDebug.test_thread_inventory_dumps_stack_for_non_daemon_alive_thread

Evidence:
tests/unit/test_check_admission.py::TestTimingDebug (all 8 cases, incl. the
3 new ones) -- pytest exit=0, 8 passed
frob test --base main -- touched=11 python exit=0 duration=38.04s

Audit performed (no un-converted timeout-abandon ThreadPoolExecutor pattern
found beyond T-3708's lang/vet fix): grepped every ThreadPoolExecutor/
future.result(timeout=.../shutdown(wait=False) site in src/frob/check,
src/frob/gates, src/frob/vet, src/frob/lang -- every remaining
ThreadPoolExecutor use is a plain `with ThreadPoolExecutor() as x: ...`
block whose __exit__ already blocks on full join before returning, so
none of them can itself be the source of a thread still alive AT atexit
(a hang inside one of those blocks would keep run_check from returning at
all, not merely delay atexit after a clean return). Landed instrumentation
only, per the ticket's own "if not obvious, land the instrumentation"
guidance -- no ThreadPoolExecutor/thread fix applied this round.

CI ${budget} check: verified .github/workflows/ci.yml's Windows Test step
(line ~1536) and macOS Test step (line ~251) both already use the
canonical no-space curly-brace form (`${budget}s`), matching the fix
T-3692/AT already landed (confirmed via `git show 98652fe20` diff, which
converted the old bare `$budget s` form to this one). No unexpanded
`${budget}` instance remains in the file; no edit made there.

Filed: none (no new out-of-scope work found)

Gates: frob check --ticket T-3713 clean except DEPR006 (pre-existing,
repo-wide "deprecated-baseline lock producer looks ABANDONED" finding,
unrelated to this ticket's scope -- 1383 commits touched src/frob since
the lock was last stamped, well before this ticket started)

### Changed
```
 tickets/T-3713/done-report.md | 56 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-3713/ticket.md      | 13 +++++++++-
 2 files changed, 68 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_check_admission.py::TestTimingDebug::test_thread_inventory_silent_when_disabled` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestTimingDebug::test_thread_inventory_lists_every_live_thread` (pytest node id, verified passing when recorded)
- `tests/unit/test_check_admission.py::TestTimingDebug::test_thread_inventory_dumps_stack_for_non_daemon_alive_thread` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 1 error(s), 4313 warning(s), 915 waived
- error-findings: DEPR006@frob-deprecated-baseline.lock.json
