---
id: T-3549
title: 'Windows CI KeyboardInterrupt round 2: execnet gateway teardown interrupt_main(),
  not console sharing'
state: done
kind: bug
origin: human
created: '2026-08-31'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 cannot be satisfied by a local test
  actor: logan
  at: '2026-08-31'
  old_length: 5337
  new_length: 5943
evidence:
- tests/unit/test_release_workflow_gate.py::TestCiWindowsLegAdvisoryOnly::test_build_job_continue_on_error_is_windows_only
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Round 2 (T-3540's console-sharing fix, run 33361224273, HEAD 8d4c18055, job 99392812476, WITH the fix live): windows-latest STILL DID-NOT-COMPLETE -- exitstatus=2 INTERRUPTED, collected=13000 (partial), failed=0 (T-3539's Cplace fix held: the suite is genuinely clean up to the interrupt point, ~1%). Dropping -NoNewWindow from Start-Process made no observable difference -- ruling out the console-sharing/CTRL_BREAK_EVENT-broadcast hypothesis (or showing it was incomplete): the interrupt still happens, in the same shape, at the same ~1% point.

RE-DIAGNOSIS. No "::error::Windows Test step exceeded" message appears in the log, so Wait-Process did NOT time out -- the pytest child process itself exited with the KeyboardInterrupt, internally, before the 1500s budget. That rules out an EXTERNAL kill/console-broadcast entirely: the interrupt is raised INSIDE the Python process by Python's own code, not delivered from outside.

MECHANISM FOUND (read directly from the installed package, not guessed): execnet (pytest-xdist's transport layer), .venv/lib/python3.11/site-packages/execnet/gateway_base.py:1234-1249, `Gateway._terminate_execution`:

    def _terminate_execution(self) -> None:
        # called from receiverthread
        self._trace("shutting down execution pool")
        self._execpool.trigger_shutdown()
        if not self._execpool.waitall(5.0):
            self._trace("execution ongoing after 5 secs, trying interrupt_main")
            if sys.platform != "win32":
                os.kill(os.getpid(), 2)  # send ourselves a SIGINT
            elif interrupt_main is not None:
                interrupt_main()
            if not self._execpool.waitall(10.0):
                os._exit(1)

`interrupt_main()` is `_thread.interrupt_main()` -- schedules a KeyboardInterrupt to be raised on the process's OWN main thread the next time the interpreter checks for signals (delivered from whatever thread happens to be blocked at that moment, e.g. inside a `threading.py` wait call -- exactly matching the observed `threading.py:359: KeyboardInterrupt` frame in every one of these incidents). `_terminate_execution` is `receiverthread`'s response to a Gateway's own channel/connection closing while its execution pool has NOT finished within 5 seconds -- i.e. a WORKER gateway shutting down uncleanly (crashed, or its I/O pipe closed) races the controller's own receiver thread into this 5s-then-interrupt-main escalation. This is entirely internal to execnet/pytest-xdist's own transport-teardown code, independent of any Windows console/process-group sharing -- consistent with T-3540's fix making no difference.

CIRCUMSTANTIAL SUPPORT: the log's "bringing up nodes..." line appears printed TWICE in a row (once is normal for a single xdist session start) immediately before the interrupt -- consistent with a worker gateway needing to be re-established/restarted during startup, the exact class of event that races `_terminate_execution`. `-n auto --dist=loadgroup` (pyproject.toml addopts) spins up one worker process per CPU on the runner; GH's windows-latest hosted runners are known to be slower to spawn/import a Python subprocess than ubuntu-latest/macos-latest for equivalent work, plausibly slow enough here to trip execnet's own internal handshake/liveness timeouts during worker bring-up.

RULED OUT this round: pytest-timeout thread-method (T-3540's own diagnosis, re-confirmed: os._exit(1), never an interrupt); the T-3506 portable lock's Windows branch (_msvcrt_acquire_blocking, src/frob/process/_lock.py:79-99) -- read directly: an unbounded `while True: msvcrt.locking(LK_NBLCK) except OSError: time.sleep(0.05)` polling loop with NO timeout and no call that could itself raise KeyboardInterrupt or anything KeyboardInterrupt-adjacent -- a genuine deadlock there would HANG past the 1500s budget (a different, distinguishable failure shape: the "::error::...exceeded" message WOULD appear), not interrupt at ~1%/under a minute; no os.kill(CTRL_C_EVENT)/GenerateConsoleCtrlEvent call anywhere in tests/ or src/, nor in execnet/xdist/_pytest themselves (grepped all three, zero hits) -- this is not a test calling a signal API, it is xdist's own internal teardown machinery.

FIX (implemented in this ticket, since it is a small, low-risk, already-touched-by-T-3540 CI-config change -- NOT a code fix to execnet, which is third-party): drop `-n auto --dist=loadgroup` from the windows-latest Test step specifically (still runs with xdist on ubuntu-latest/macos-latest, where this mechanism has not been observed to misfire) -- eliminates the entire execnet-gateway-teardown/interrupt_main() pathway on Windows by not spawning any xdist worker gateways there at all. Verify by re-running windows-latest and confirming the suite reaches a stable completed (not INTERRUPTED) result -- I cannot verify this fix's real-world effect without a real Windows CI run (no local Windows box), so treat this as diagnosed-and-attempted, not confirmed, until the next windows-latest run reports back. If it does NOT resolve this (e.g. some other execnet/threading interaction persists even single-process), the next step needs someone with an actual Windows dev box to reproduce interactively and bisect further -- this diagnosis is as far as log analysis alone can go.

Filed under T-3505 (Windows portability epic).



frob:waive BUG002 reason="this defect (execnet gateway teardown interrupt_main() on a Windows worker gateway close) only reproduces on real windows-latest CI infrastructure -- there is no local, deterministic way to force an xdist worker gateway close race in a pytest node id; the fix (dropping xdist entirely on the windows leg via -p no:xdist) is verified by re-running windows-latest and observing whether the suite completes, tracked as a windows-portability re-measurement follow-up, not by a unit test -- and is explicitly disclosed as unverified in this ticket's own body pending that real run"