---
id: T-3577
title: 'Fix windows-latest CI hang: unbounded msvcrt self-deadlock + untimed subprocess
  drain hang'
state: queued
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
- src/frob/process/_lock.py
- tests/system/conftest.py
- tests/conftest.py
- .github/workflows/ci.yml
- tests/unit/test_process_lock.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Evidence chain measured across CI runs 33370059331 and 33376126399 (windows-latest, -v --full-trace, T-3560 instrumentation).

Symptom: the FIRST tests/system test invokes the frob CLI via tests/system/conftest.py run() (win32 branch: subprocess.run(capture_output=True, timeout=DEFAULT_RUN_TIMEOUT_S=100)). The child hangs; run() blocks in communicate()s reader-thread Thread.join (frames: tests/system/conftest.py:149 -> subprocess._communicate -> threading.py:1169). At ~4 minutes a KeyboardInterrupt lands in the main thread and pytest aborts the whole SESSION (exitstatus 2 INTERRUPTED at [1%]).

(a) Finding: pytest-timeout 2.4.0 is NOT the sender. Grepped for interrupt_main/KeyboardInterrupt in its installed source: zero hits. Its two handlers are timeout_sigalrm (SIGALRM, POSIX-only, calls pytest.fail) and timeout_timer (thread method, calls os._exit(1), a hard kill not a raised exception). Neither raises KeyboardInterrupt. The interrupt is a genuine external signal or a downstream Popen mechanism, consistent with ci.ymls own T-3560 conclusion that xdist/execnet was already ruled out via -p no:xdist.

(b) Root cause, two closed suspects:
  1. subprocess.runs OWN internal timeout handling: on TimeoutExpired it calls process.kill() then retries communicate() a SECOND time with NO timeout to drain remaining output. If the killed child left a grandchild alive still holding the inherited stdout/stderr pipe write-end open (Windows CreateProcess duplicates ALL inheritable handles into every spawned child, unlike POSIX close-on-exec-by-default), the pipe never reaches EOF and this untimed second communicate() blocks forever in Thread.join -- matches the observed frames exactly.
  2. src/frob/process/_lock.pys msvcrt backend: _msvcrt_acquire_blocking (the blocking/timeout=None case of _portable_flock_acquire_windows) is an UNBOUNDED retry-forever poll loop with no same-process reentrancy guard, unlike derived_state_locks POSIX-side _process_held_counts registry. Other ported call sites (frob.tickets._store/_land/_leases/_land_queue/_mutation_sweep_queue/_new_renumber/_land_git_ops, frob.serve._socketd, frob.testing._coverage_wait) call portable_flock_acquire directly with no such guard. msvcrt.locking is not re-entrant even on the same fd/process, so any nested same-process re-acquire of the same lock self-deadlocks FOREVER on Windows only (POSIX flock re-lock on the same fd is a no-op).

(c) Fix scope: bound _msvcrt_acquire_blockings poll loop with a ceiling instead of infinite retry (turns a silent forever-hang into a loud bounded failure on Windows); make the win32 branch of tests/system/conftest.pys run() survive a hung child without relying on subprocess.runs own untimed drain retry (explicit process-tree kill + bounded read). Extend tests/unit/test_process_lock.py with a same-process re-entry case using the existing monkeypatched-backend harness.

(d) Revert T-3560 instrumentation in the SAME land per that tickets own contract: -v --full-trace in .github/workflows/ci.ymls windows Test step, and the SIGBREAK faulthandler registration (_install_sigbreak_faulthandler) in tests/conftest.py.

Cites runs 33370059331 and 33376126399.