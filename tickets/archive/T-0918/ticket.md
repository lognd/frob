---
id: T-0918
title: Wire derived_state_lock exclusive side into dup/graph cache rebuilders (needs
  process-wide reentrancy signal)
state: done
kind: bug
origin: human
created: '2026-07-26'
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
- src/frob/dup/_pipeline.py
- src/frob/graph/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense process-held reentrancy-count rationale into T-0918 body
  actor: logan
  at: '2026-09-19'
  old_length: 2903
  new_length: 4119
evidence:
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_standalone_rebuild_takes_exclusive
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_nested_inside_shared_holder_does_not_deadlock
- tests/unit/test_process_lock.py::TestDerivedStateWriteLock::test_concurrent_separate_process_writer_still_blocked
- tests/test_graph.py::TestBuildIncremental::test_stats_sum_source_and_doc_counts_not_difference
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0879 wired `derived_state_lock(root, exclusive=True)` into the two
writers where it is safe to do so unconditionally: `frob.mutate.
run_mutations` and `frob.doctor.run_diagnosis`. Both are ALWAYS invoked
standalone (frob mutate; frob ticket close/land's mutation-evidence
obligation; frob doctor) -- never nested inside an already-locked `frob
check` run -- confirmed by grepping every production call site.

`frob.dup.find_clones` and `frob.graph.build_graph` were deliberately
NOT wired, because they are NOT always standalone: both are called from
inside `frob check`'s own gate execution (`frob.check._python._run_dup`,
and build_graph from check/_python.py and gates/_prework.py) while the
main thread already holds check's own SHARED `derived_state_lock` for
the run's whole duration. Those gate functions run in a
`ThreadPoolExecutor` worker thread, a DIFFERENT thread than the one that
acquired the shared lock.

`derived_state_lock`'s re-entrancy guard (`frob.process._lock._lock_
local`) is per-thread, and `flock(2)` itself does not grant same-process
re-entrancy across different open file descriptions: a worker thread
requesting EXCLUSIVE on the same lock file would genuinely block against
the main thread's SHARED hold, which cannot release until that worker
returns -- a real same-process deadlock, not just a logical contract
violation. This was proven with a citation of POSIX flock(2) semantics
(distinct fds compete even within one process) plus a direct trace of
`_run_check_with_skips` -> `_python_tasks` -> `ThreadPoolExecutor` ->
`_run_dup`/gates -> `find_clones`/`build_graph`.

Wiring the exclusive lock into `find_clones`/`build_graph` unconditionally
would deadlock every real `frob check` run that reaches the dup gate or a
graph rebuild -- worse than the race T-0879 exists to close. Doing it
correctly needs a PREREQUISITE this ticket's scope (`src/frob/dup/**`,
`src/frob/graph/**`) cannot provide on its own: a process-wide (not
thread-local) "is this root's derived-state lock already held by ANY
thread in this process" signal, either exposed from
`src/frob/process/_lock.py` itself (out of T-0879's scope, `derived_
state_lock`'s own module `T-0859`/T-0879 scope excludes `process/**`), or
threaded through as an explicit "caller already holds the lock" flag from
`src/frob/check/**`/`src/frob/gates/**` (also out of scope) down through
`build_graph`/`find_clones`'s call signature.

Scope for this follow-up: `src/frob/process/_lock.py` (expose the
process-wide reentrancy signal) plus `src/frob/dup/_pipeline.py` and
`src/frob/graph/__init__.py` (consult it in `find_clones`/`build_graph`
before taking EXCLUSIVE, falling back to a same-process no-op when the
process already holds ANY mode of the lock). `src/frob/check/**` and
`src/frob/gates/**` are read-only reference points, not touched.

See T-0879's Done report for the full deadlock trace and citations.

<!-- narrative-moved:src/frob/process/_lock.py:314:T-0918 -->
frob:ticket T-0918
T-0918: PROCESS-wide (not thread-local) reentrancy signal. `_lock_local`
above only answers "does THIS thread already hold the lock" -- it says
nothing about a SIBLING thread in the same process (e.g. `frob check`'s
`ThreadPoolExecutor` gate workers) holding it concurrently. `flock(2)`
itself gives no same-process reentrancy across distinct open file
descriptions: a worker thread that naively requested EXCLUSIVE while the
main thread already holds SHARED on the same lock file would genuinely
block against its own process's other thread -- a real deadlock, not a
logical contract violation (see T-0879's Done report and this module's
own docstring for the flock(2) citation). `_process_held_counts` tracks,
per lock-file path, how many distinct real OS-level acquisitions (across
ALL threads, ANY mode) are currently outstanding in THIS process; it is
incremented exactly once per first-time (non-reentrant) acquire and
decremented exactly once when that acquisition's final release happens,
guarded by `_process_registry_lock` since multiple threads race on it
concurrently. `derived_state_write_lock` below is the only reader.