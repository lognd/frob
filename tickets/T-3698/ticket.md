---
id: T-3698
title: os.kill(pid, 0) win32 footgun still live in gates/_fix_engine_shared.py::_pid_alive
state: in-progress
kind: bug
origin: human
created: '2026-09-02'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_fix_engine_shared.py
- tests/gates_suite/test_fix_engine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates_suite/test_fix_engine.py
  reason: adding regression test for the _pid_alive delegation fix
  actor: logan
  at: '2026-09-02'
designated_repro_test: null
acceptance:
- text: 'Given frob.gates._fix_engine_shared._pid_alive, when a win32-shaped test
    monkeypatches os.kill to raise/assert-not-called, then the fixed implementation
    never calls os.kill and instead delegates to frob.process._pid_liveness.pid_alive
    (before: test calling os.kill / after: test proves no os.kill call and correct
    liveness result via the delegated probe)'
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while researching T-3686/T-3696 (PLATFORM002 detector). frob.gates._fix_engine_shared._pid_alive (T-3526) still calls os.kill(pid, 0) directly -- the SAME win32 Ctrl+C-broadcast footgun T-3686 fixed in frob.check._pid_alive. This is NOT the sanctioned frob.process._pid_liveness module. Its own docstring says it is 'a local copy of frob.check._pid_alive' kept separate to avoid a layering cycle (frob.gates sits below frob.check per docs/rework.md), so it cannot simply import frob.check._pid_alive either -- but it CAN import frob.process._pid_liveness.pid_alive instead, the same way frob.mutate._journal and frob.tickets._land already do (frob.process sits below frob.gates in the same layering rule; verify before landing). Fix: delegate _pid_alive to frob.process._pid_liveness.pid_alive instead of calling os.kill directly. Left unfixed by T-3696 deliberately (out of a detector-only ticket's scope) -- T-3696's new PLATFORM002 gate will legitimately flag this exact site once it lands; either fix this ticket before removing any T-3696 frob:waive on it, or land this first.