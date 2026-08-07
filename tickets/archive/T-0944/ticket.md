---
id: T-0944
title: 'frob check self-deadlocks: derived.lock opened twice, READ+pending WRITE same
  pid'
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
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
## Description

Every `frob check --ticket T-XXXX --only <anything>` invocation in this
worktree (agent-a5842ed351bbd927e) hangs indefinitely instead of
completing. Confirmed via `/proc/<pid>/fd` and `/proc/locks`, not a slow
computation under contention:

- The `frob check` process opens `.frob/derived.lock` TWICE, holding two
  separate file descriptors (fd 3 and fd 4) to the same inode.
- `/proc/locks` shows the SAME pid holding a `READ` (shared) `FLOCK` on
  one fd and a pending `WRITE` (exclusive) `FLOCK` request on the other:
  ```
  31: FLOCK  ADVISORY  READ 1008549 08:30:1142126 0 EOF
  31: -> FLOCK  ADVISORY  WRITE 1008549 08:30:1142126 0 EOF
  ```
- `flock(2)` has no cross-fd reentrancy/upgrade semantics within one
  process -- a second, independent open+`LOCK_EX` request against a file
  the same process already holds `LOCK_SH` on (via a different fd) blocks
  forever, since the shared lock is never released before the exclusive
  request is made.
- `src/frob/process/_lock.py`'s own module docstring already flags this
  exact hazard class ("an `always os.open + flock` implementation would
  self-deadlock the moment a [...] `ThreadPoolExecutor` gate workers)
  holding it concurrently") and tracks `_process_held_counts` to guard
  against same-process reentrancy -- but that tracking evidently does not
  cover whatever two call sites raced here (one held via
  `derived_state_lock(..., exclusive=False)`, another requesting
  `derived_state_write_lock`/`exclusive=True` before the first is
  released).
- Reproduced twice, with two different `--only` gate selections
  (`scope`, then `prework`) against the same worktree -- not specific to
  one gate's code path, so likely in shared `check` runner
  setup/teardown around `_lock.py`, not gate-specific logic.

## Plan (for whoever picks this up)

1. Reproduce under `py-spy dump` or a debug build to get both call
   stacks holding fd3 (shared) and fd4 (pending exclusive) at the moment
   of hang.
2. Audit `frob.process._lock`'s `_process_held_counts`/reentrancy guard
   for the gap that let a second `os.open` + `flock` happen before the
   first shared lock in the SAME process was released or upgraded
   in-place (upgrade-in-place on the same fd via `LOCK_EX` again is safe
   and non-blocking against oneself; opening a NEW fd and locking THAT is
   not).
3. Fix by (a) tracking open fds per-process so a nested acquire reuses
   the existing fd/lock rather than opening a new one, or (b) removing
   whatever code path re-derives `root` and re-opens the lock file
   instead of reusing an already-lock-held context manager.

Filed while working T-0931 (comment-DSL `frob:raises` reconciliation);
that ticket needed `frob check` to record evidence/close and this bug
blocks it entirely in that worktree. Not fixed there -- `src/frob/
process/_lock.py` is outside T-0931's declared scope
(`src/frob/arch/**`, `src/frob/gates/**`, plus the doc/test files
scope-added for the rename itself).

## Drop reason
- 2026-07-27: duplicate of the T-0933 same-pid deadlock, fixed and landed (absorbed by T-0933)