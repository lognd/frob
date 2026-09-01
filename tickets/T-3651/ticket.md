---
id: T-3651
title: 'win32: CREATE_NO_WINDOW on tool spawns to stop console-shared SIGINT'
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
- src/frob/process/_guard.py
- tests/unit/test_process_guard.py
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
Run 33513484322: T-3648's instrumentation DELIVERED. The diag child
printed:

  T-3648-SIGNAL: received SIGINT (signum=2) at frame=<threading.py:355 wait>

at ~1.5s, immediately after the first tool spawns
(FROB_WIN32_SPAWN_DEBUG showed git rev-parse and `ruff format --check .`
spawned with creationflags=512, i.e. CREATE_NEW_PROCESS_GROUP applied).
So: a REAL CTRL_C_EVENT reaches frob's process even though children are
in their own process GROUP -- because a new process group still SHARES
THE CONSOLE. Any console-attached child (or its runtime) that calls
GenerateConsoleCtrlEvent(CTRL_C_EVENT, 0) signals EVERY process on the
console, groups notwithstanding. The correlation with the ruff spawn
makes the tool child (or uv shim) the sender.

Fix: in _win32_isolate_console_group (src/frob/process/_guard.py),
spawn tool children with CREATE_NO_WINDOW (0x08000000) in addition to
(or instead of) CREATE_NEW_PROCESS_GROUP -- a child with no console
cannot signal ours. The check pipeline's children are non-interactive
with piped stdio, so no functionality is lost. Keep the spawn-debug
instrumentation; print the new flags value. Also note the SAME class
explains the in-suite interrupt: this very run's Windows suite got
KeyboardInterrupt-INTERRUPTED at 13123 collected ~15 min in (pytest
process group shares the console with frob-check children's tools).
Acceptance: next CI run's diag shows exit code 0 or a genuine GATE
result (not 130), and the Windows Test step completes without a
KeyboardInterrupt abort. Keep the diag step in place until then.
Scope: src/frob/process/_guard.py + tests/unit/test_process_guard.py
(+ ci.yml only if the diag needs a tweak).
