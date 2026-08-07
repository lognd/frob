---
id: T-1191
title: 'perf: fix 4 unwaived PERF005/PERF008 findings found in T-0204 verification
  close'
state: dropped
kind: bug
origin: human
created: '2026-07-29'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/vet/_taint.py
- src/frob/arch/_ffi.py
- src/frob/serve/_watch.py
- tests/test_serve_watch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
T-0204 verification close (2026-07-29) found gate:PERF is NOT honestly at
zero unwaived right now, despite T-1041's residue burn-down: 4 unwaived
findings exist on current main-plus-this-branch:

- PERF005 src/frob/vet/_taint.py:134 -- recursive call to
  `_assigned_names` with no provable termination measure.
- PERF008 src/frob/arch/_ffi.py:298 -- `pat.search(...)` inside a loop
  with loop-invariant arguments (reaches `frob.excludes.walk_pruned`, a
  fs-walk effect).
- PERF008 src/frob/serve/_watch.py:169 -- `watch_tick(...)` inside a loop
  with loop-invariant arguments (reaches
  `frob.process._guard.guarded_subprocess_run`, a spawn effect).
- PERF008 tests/test_serve_watch.py:86 -- `_warm._repo_dirty_key(...)`
  inside a loop with loop-invariant arguments (same spawn-effect chain).

These are new since T-1041 (not present in its own closing measurement)
-- either real code added afterward introduced them, or they are newly
detected by a PERF008 rule refinement. Either way this is live,
unwaived PERF debt today: fix each site (add a termination measure, or
hoist/memoize the loop-invariant call) or add a reasoned
`frob:waive PERF005`/`frob:waive PERF008` per site, then re-verify
`frob check --only gates-native` shows 0 unwaived PERF findings again.

## Failure log
- 2026-07-29 attempt 1: T-0204's cited PERF005/PERF008 findings do not reproduce on current main: full frob check --ticket T-1191 shows gate:PERF at 0 errors, 4 warnings, 97 waived, none matching vet/_taint.py _assigned_names, arch/_ffi.py:298, serve/_watch.py:169, or test_serve_watch.py:86 -- already resolved before this dispatch

## Drop reason
- 2026-07-29: not reproducible: the PERF005/PERF008 findings from T-0204's close-time measurement do not exist on current main -- verified via full foreground scoped checks (gate:PERF 0 errors) and structural-termination reading of the one named function; transient-measurement class