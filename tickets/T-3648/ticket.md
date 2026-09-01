---
id: T-3648
title: win32 frob check dies by injected KeyboardInterrupt at executor thread start
state: queued
kind: bug
origin: human
created: '2026-09-01'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
- src/frob/process/_guard.py
- src/frob/process/_pytest_spawn.py
- src/frob/check/__init__.py
- src/frob/__main__.py
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
Run 33491468339: the round-12 diag ran END TO END and captured the full traceback after 12 rounds of harness fights. frob check on win32, on a tiny valid fixture, at ~1.5s elapsed:

  File 'src/frob/check/__init__.py', line 1187, in _run_tasks_concurrently
    fut = executor.submit(fn)
  ...concurrent/futures/thread.py:203 _adjust_thread_count -> t.start()
  ...threading.py:999 start -> self._started.wait()
  ...threading.py:355 wait -> waiter.acquire()
  KeyboardInterrupt
  -> frob prints 'frob: interrupted', exits 130 (__main__.py:119)

On Windows, a lock acquire on the MAIN thread is interruptible: CPython raises KeyboardInterrupt there when the process's SIGINT console event is set. Nothing external sent Ctrl-C at 1.5s -- something INSIDE frob's early check pipeline sets the SIGINT event. Suspects, in order: (1) a child process spawned by the check pipeline created WITHOUT CREATE_NEW_PROCESS_GROUP that forwards a console ctrl event to the shared group -- measured: guarded_subprocess_run (src/frob/process/_guard.py, called by every frob.check tool runner) calls plain subprocess.run with no creationflags at all, so any spawned tool child shares the parent's console process group; a Ctrl event delivered to that group (by the CI runner, a wrapper script, or Windows job-object teardown) reaches the frob main process itself, not just the child. (2) T-3565's SIGBREAK signal.signal handler (win32-specific). (3) signal.set_wakeup_fd/faulthandler interplay in frob's startup. CONNECTION TO THE SUITE HANG: in-suite (test_cli_check.py) the same frob-check child HANGS >120s instead -- if the child's console-event pollution interrupts ITS OWN main thread here, under the suite the event may instead land in a different process of the group and turn into the parent's communicate() wait (T-3577's exact symptom).

Approach: reproduce via the diag harness locally is impossible (WSL); iterate VIA CI: add a temporary instrumented variant of the diag child that (a) installs a logging SIGBREAK/SIGINT handler printing the signal + stack before re-raising, (b) prints every subprocess spawn (cmd + creationflags) from the check pipeline via an env-gated debug hook (FROB_WIN32_SPAWN_DEBUG=1 -- add it, gated, harmless elsewhere), then read the next run's diag output to name the spawning call site. Fix at the source (creationflags/handler discipline), then leave the diag step in place until a run shows frob check diag exit code: 0 (or a genuine nonzero GATE result) on win32.