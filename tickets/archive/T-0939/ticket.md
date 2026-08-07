---
id: T-0939
title: 'check --only scope hangs: derived.lock self-deadlock (same pid holds READ+WRITE*
  simultaneously)'
state: dropped
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/gates/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
Observed while verifying T-0718: `uv run frob check --ticket <id> --only scope` hung
indefinitely (multiple repeat attempts, 300s+ each, across varying system load from
load-average 17 down to under 1) in worktree
/home/logan/projects/frob/.claude/worktrees/agent-a71338f817a4d2945. `lslocks` showed the
SAME pid holding both a READ and a WRITE* (pending/blocked) flock on the same
.frob/derived.lock file at the same time:

  frob  <pid>  FLOCK  WRITE*  .../a71338f817a4d2945/.frob/derived.lock
  frob  <pid>  FLOCK  READ    .../a71338f817a4d2945/.frob/derived.lock

This looks like the process opened a second fd on derived.lock and requested LOCK_EX
while its first fd still held LOCK_SH -- flock(2) locks are associated with the open
file description, not the process, so two different fds in the same process can
deadlock each other exactly like two different processes would. src/frob/process/_lock.py
already has same-process reentrancy tracking (_process_held_counts, see its module
docstring re: avoiding exactly this self-deadlock) -- the --only scope code path
apparently reaches a second derived_state_lock acquisition that bypasses/misses that
tracking. Reproduced 3x in a row with fresh invocations (fresh pids each time, same
symptom). Worked around verification by calling frob.gates.scope_matches directly in
Python instead of through the CLI gate pipeline.

Investigate src/frob/process/_lock.py's derived_state_lock and whatever in the "scope"
check-stage wiring (src/frob/gates/__init__.py around scope_gate/PRE001 prework-sweep
loading, or app/check_runner.py's --only dispatch) acquires it twice without releasing
the first handle.

## Drop reason
- 2026-07-27: same-pid READ+WRITE derived.lock deadlock: root-caused and fixed by T-0933 (canonical registry key), landed 91180266 (absorbed by T-0933)