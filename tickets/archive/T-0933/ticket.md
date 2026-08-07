---
id: T-0933
title: frob check --only scope/prework self-deadlocks on derived_state_lock (T-0918
  regression)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/process/_lock.py
- src/frob/check/__init__.py
- src/frob/dup/_pipeline.py
- src/frob/graph/__init__.py
- tests/unit/test_process_lock.py
- docs/modules/process.md
- frob.lock
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_process_lock.py
  reason: T-0933 regression test lives here
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/process.md
  reason: T-0933 root-cause note for derived_state_write_lock canonical keying
  actor: logan
  at: '2026-07-27'
- op: add
  glob: frob.lock
  reason: T-0933 ack of process.md doc-drift touched frob.lock
  actor: logan
  at: '2026-07-27'
evidence:
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_nested_inside_shared_holder_does_not_deadlock
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_concurrent_separate_process_writer_still_blocked
- tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_shared_unresolved_then_nested_write_resolved_does_not_deadlock
- tests/unit/test_process_lock.py::TestProcessRegistryCanonicalKey::test_write_resolved_then_nested_shared_unresolved_agrees
designated_repro_test: null
threat: null
component: null
---
CRITICAL: `frob check --only scope` (and `--only prework`, which also
triggers `frob.graph.build_graph`) reproducibly self-deadlocks in EVERY
worktree since T-0918's `derived_state_write_lock` landed on `main`
(commit d0af2382, "Wire derived_state_lock exclusive side into dup/graph
cache rebuilders").

Reproduction (T-0924's own worktree, and confirmed via `lslocks` showing
the identical signature in several OTHER concurrently-running worktrees
at the same moment -- this is not one worktree's local corruption):

```
cd <any worktree>
timeout 30 uv run frob check --only scope --ticket <any> &
# a few seconds later:
lslocks | grep derived.lock
```

Observed: the SAME pid holds both a READ (shared) and a WRITE* (blocked
exclusive) lock on its own `.frob/derived.lock` simultaneously -- a
same-process self-deadlock, not cross-process contention (confirmed via
`/proc/<pid>/wchan` = `futex_wait_queue` and the process making zero
progress across a 500s wait with system load otherwise low).

`derived_state_write_lock` (src/frob/process/_lock.py) is designed to
no-op when `_process_already_holds(root)` is True (i.e. some thread in
this process already holds `derived_state_lock` for the same `root`),
specifically to avoid this exact self-deadlock when a gate worker thread
calls `frob.graph.build_graph`/`frob.dup.find_clones` while `frob.check`'s
main thread holds a run-wide SHARED lock (T-0859). Both call sites do
route through `derived_state_write_lock` (verified: `frob/graph/
__init__.py:517`, `frob/dup/_pipeline.py:1916`), so the no-op guard is
being bypassed rather than absent -- most likely `_process_already_holds`
is keying on a `root` value (via `_derived_lock_path`/`str(path)`) that
does not string-match the `root` `frob.check.run_check`'s outer
`derived_state_lock(root, exclusive=False)` call used (e.g. resolved vs
unresolved path, or a differently-constructed `Path` for the same
directory) -- same physical inode, different dict key, so the process-
wide reentrancy signal reads False and a real second EXCLUSIVE `flock()`
is attempted against the process's own SHARED hold on a different open
file description. That is a hypothesis, not a confirmed root cause --
needs a real fix in `src/frob/process/_lock.py` /
`src/frob/check/__init__.py` (whichever passes the mismatched root) plus
a regression test that actually runs `frob check --only scope`/`prework`
end-to-end (existing `tests/unit/test_process_lock.py` tests appear to
exercise the lock primitives directly/synthetically, not through the real
`frob.check` dispatch path, so they did not catch this).

Impact: blocks `frob check --only scope` and `--only prework` (and
likely any `--only` selection that reaches a dup/graph rebuild) in EVERY
worktree of this repo until fixed -- a hard stop for any agent trying to
gate-verify a ticket via the sanctioned chunked `--only` loop
(docs/guides/agent-playbook.md section 3b).

Filed while re-verifying T-0924 after merging main; T-0924 itself could
not get a clean `--only scope`/`--only prework` post-merge run because of
this and used pre-merge evidence plus pytest test evidence instead (see
its Done report).