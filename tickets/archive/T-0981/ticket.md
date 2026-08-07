---
id: T-0981
title: 'dup_gate deadlocks under frob check: derived_state_write_lock reentrancy blind
  to ProcessPoolExecutor workers'
state: done
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
- docs/modules/process.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_real_pool_worker_under_parent_shared_holder_completes
- tests/unit/test_process_lock.py::TestCrossProcessPoolInheritance::test_independent_process_without_marker_still_blocks
designated_repro_test: null
threat: null
component: null
---
Found while working T-0974 ("enable [dup].enforce=true by default").

`frob check`'s main run wraps its whole duration in
`derived_state_lock(root, exclusive=False)` (SHARED,
src/frob/check/__init__.py:582 and 3 other call sites). `dup_gate` (the
"clones" job) is dispatched into a `ProcessPoolExecutor`
(`_PROCESS_POOL_GATES`, src/frob/gates/__init__.py ~line 9994) for real
CPU parallelism (T-0415). `find_clones` (src/frob/dup/_pipeline.py)
unconditionally wraps its ENTIRE body in
`derived_state_write_lock(root)` (EXCLUSIVE-or-noop,
src/frob/process/_lock.py).

`derived_state_write_lock`'s reentrancy check (`_process_already_holds`,
src/frob/process/_lock.py) is a PROCESS-WIDE in-memory registry -- it only
sees state set by threads in the SAME OS process. Because "clones" runs in
a genuinely separate forked/spawned process (ProcessPoolExecutor, not
ThreadPoolExecutor), that worker's `_process_already_holds(root)` reads
False even though `frob check`'s main process already holds SHARED. The
worker then takes the real cross-process path and calls
`flock(LOCK_EX)`, which blocks forever against the main process's SHARED
hold -- and that SHARED hold cannot release until the worker (which is
itself the thing it's waiting on) returns. This is a genuine, reproducible
DEADLOCK, not merely slowness, for any `frob check` run where `[dup].
enforce=true` and the clones job actually reaches this lock (i.e. every
run, since `find_clones` takes the lock unconditionally, not just on
cache-miss).

Live repro (this ticket, 2026-07-27): set `[dup].enforce=true` (no
`native_rungs`), delete `.frob/dup.db`, run `uv run frob check --only
clones`. The run exceeded 120s/200s+ with near-zero CPU (I/O-wait, not
compute). `lslocks` showed:

```
python  <pid-worker>  FLOCK  WRITE*  ...  .frob/derived.lock   # blocked
frob    <pid-main>     FLOCK  READ    ...  .frob/derived.lock   # held
```

confirming the exact mechanism above. This likely explains T-0399's
original "~150s blowout" measurement too -- it was plausibly this
deadlock (or very close to it) rather than genuine fingerprinting compute
cost, since `derived_state_write_lock`'s own module docstring already
documents (T-0918) that its reentrancy signal only works for a
`ThreadPoolExecutor` worker THREAD nested in the main process, and
explicitly disclaims the process-pool case as a "documented latent gap,
not an observed regression" with "no current production call site" doing
this -- but `_PROCESS_POOL_GATES` including `"clones"` (T-0415, landed
separately) IS exactly that call site; the two tickets' assumptions never
got cross-checked against each other.

T-0974 could not safely flip `[dup].enforce=true` on by default given
this: doing so would make `frob check`'s clones stage hang (not just run
slow) for any cold-cache run, which is strictly worse than the status quo
(off by default, gate never runs).

Fix needs design, not a quick patch, and touches files outside T-0974's
declared scope (`src/frob/process/_lock.py` for the locking primitive
itself, and/or `src/frob/gates/__init__.py`'s `_PROCESS_POOL_GATES`
executor-topology decision, which T-0415 deliberately set for "clones").
Candidate directions (not evaluated in depth): (a) move "clones"
specifically out of `_PROCESS_POOL_GATES` back onto the thread pool --
the native Rust calls inside `find_clones` likely release the GIL enough
for real parallelism even on a thread, but this partially undoes T-0415's
reasoning for this one gate and needs re-measurement; (b) give
`derived_state_write_lock` a real cross-process-but-same-run reentrancy
signal (e.g. a marker file/env var the parent `frob check` process sets
before spawning its ProcessPoolExecutor workers, checked by
`_process_already_holds` in addition to the in-memory registry); (c) have
`frob check`'s main process release its SHARED hold (or downgrade some
other way) before submitting process-pool jobs that might need the
EXCLUSIVE path, and reacquire after -- correctness-sensitive, needs care
against the exact race T-0918's docstring already warns about for the
thread case.

Scope for the ticket that picks this up: `src/frob/process/_lock.py`,
`src/frob/gates/__init__.py` (`_PROCESS_POOL_GATES`, `dup_gate`
dispatch), plus `docs/modules/process.md`/`docs/modules/gates.md` for the
corrected reentrancy-contract writeup once fixed.