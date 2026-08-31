## Done report

Changed:
- src/frob/process/_lock.py::_msvcrt_acquire_blocking
- src/frob/process/_lock.py::_MSVCRT_BLOCKING_ACQUIRE_CEILING_S
- tests/system/conftest.py::run (win32 branch)
- tests/conftest.py (T-3560 revert: _install_sigbreak_faulthandler removed, pytest_configure call site removed)
- .github/workflows/ci.yml (T-3560 -v/--full-trace revert; comment updated with T-3577 root cause)
- tests/unit/test_process_lock.py::TestPortableFlock::test_windows_blocking_reentry_raises_instead_of_hanging_forever (new)
- tests/system/test_run_helper_env_leak.py::TestRunHelperWin32TimeoutSurvivesAHungGrandchild (new)
- tests/unit/test_conftest_sigbreak_faulthandler.py (T-3565's test module, converted to a skip-stub -- see below)

Root cause (measured across runs 33370059331 and 33376126399):
(a) pytest-timeout 2.4.0 is NOT the KeyboardInterrupt sender -- grepped its
installed source for interrupt_main/KeyboardInterrupt: zero hits. Its two
handlers (timeout_sigalrm, timeout_timer) never raise KeyboardInterrupt;
timeout_timer hard-kills via os._exit(1).
(b) The actual hang: subprocess.run(..., timeout=100)'s OWN internal
TimeoutExpired handling calls process.kill() then retries communicate() a
SECOND time with NO timeout, to drain remaining output. Windows
CreateProcess duplicates all inheritable handles into every spawned child
(unlike POSIX close-on-exec), so a grandchild the frob CLI spawned before
being killed could keep the inherited stdout/stderr pipe open past the
kill, and that untimed second communicate() blocks forever in
Thread.join -- exactly the observed frames
(tests/system/conftest.py:149 -> subprocess._communicate ->
threading.py:1169).
Compounding, closed in the same ticket: src/frob/process/_lock.py's
_msvcrt_acquire_blocking was an unbounded same-process-reentrancy-unsafe
poll loop (msvcrt.locking is not reentrant, unlike POSIX same-fd flock) --
now bounded at 120s, raising PortableLockUnavailable instead of hanging
forever on a nested same-process re-acquire.

Fix: tests/system/conftest.py's win32 run() branch now drives
Popen/communicate itself (both reads bounded), and on TimeoutExpired kills
the whole process tree via taskkill /PID <pid> /T /F (the Windows analog
of the existing POSIX os.killpg branch) instead of relying on
subprocess.run's own untimed drain retry.

T-3560 revert (same land, per that ticket's own contract): removed
_install_sigbreak_faulthandler and its pytest_configure call site from
tests/conftest.py; removed -v --full-trace from
.github/workflows/ci.yml's windows Test step (kept -p no:xdist, T-3549,
still a real independent risk-reduction). tests/unit/test_conftest_sigbreak_faulthandler.py
(T-3565's dedicated test module for the reverted function) is kept as a
skip-stub rather than deleted: T-3565's own ticket.md scope glob still
names this path, and deleting the file made frob check crash with an
unhandled FileNotFoundError instead of reporting COV003 -- filed
separately (Filed line below) as a frob defect, not fixed here (out of
this ticket's scope).

Evidence: tests/unit/test_process_lock.py::TestPortableFlock::test_windows_blocking_reentry_raises_instead_of_hanging_forever, tests/system/test_run_helper_env_leak.py::TestRunHelperWin32TimeoutSurvivesAHungGrandchild::test_timeout_kills_process_tree_and_never_calls_an_untimed_communicate, tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout::test_run_expiry_raises_a_named_loud_error (all pytest node ids, verified passing via uv run pytest -p no:xdist)

Filed: T-3579 (frob check crashes with unhandled FileNotFoundError instead of reporting COV003 when a closed ticket's scope glob names a file that no longer exists)

Gates: uv run frob check --ticket T-3577 --budget 280 clean of NEW findings in touched files (repo-wide FAIL counts shown are pre-existing, confirmed via the tool's own "repo-wide, not filtered to this ticket" note); uv run frob test --base main 19/19 green; targeted pytest -p no:xdist runs green.

### Changed
```
 tickets/T-3577/ticket.md | 4 ++++
 1 file changed, 4 insertions(+)
```

### Evidence
- `tests/unit/test_process_lock.py::TestPortableFlock::test_windows_blocking_reentry_raises_instead_of_hanging_forever` (pytest node id, verified passing when recorded)
- `tests/system/test_run_helper_env_leak.py::TestRunHelperWin32TimeoutSurvivesAHungGrandchild::test_timeout_kills_process_tree_and_never_calls_an_untimed_communicate` (pytest node id, verified passing when recorded)
- `tests/system/test_run_helper_env_leak.py::TestRunHelperDefaultTimeout::test_run_expiry_raises_a_named_loud_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 31 error(s), 4143 warning(s), 891 waived
- error-findings: AFFECT001@src/frob/process/_lock.py, ARCH102@src/frob/process/_lock.py, ARCH102@src/frob/tickets/_land_squash.py, ARCH103@src/frob/tickets/_leases.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/tickets/_land_queue.py, COV001@src/frob/tickets/_land_squash.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/ledger-mirror-batching.md, DOC001@docs/design/macos-portability.md, DOC002@src/frob/tickets/_land_squash.py, DOC006@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_conftest_sigbreak_faulthandler.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_conftest_sigbreak_faulthandler.py, DUP001@tests/system/conftest.py, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3577, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
