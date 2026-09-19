---
id: T-draft-dfc98d31
title: Warm sweep stage's pre-commit check probes the wrong land.lock path (T-4563
  regression)
state: queued
kind: bug
origin: human
created: '2026-09-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_effects.py
- src/frob/app/ticket_runner/_land_cmd.py
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
T-4563 gated the testsuite-glob capability-ratchet auto-accept write on
_land_commit_in_progress(root), which probes root / LAND_LOCK_REL
(.frob/land.lock). For a non-rapid land, the T-1514 pre-commit unscoped
sweep (_pre_commit_unscoped_error_sweep) runs the composed-tree
`frob check` against the PERSISTENT warm sweep stage
(_ensure_warm_sweep_stage, <root>/.frob/warm-sweep-stage), not root
itself -- but land's own _land_lock is acquired against the PRIMARY
checkout root, so the lock file actually lives at <root>/.frob/land.lock.
Inside the spawned check subprocess (cwd=warm stage),
_land_commit_in_progress computes root / LAND_LOCK_REL using the WARM
STAGE as root, landing at <root>/.frob/warm-sweep-stage/.frob/land.lock
-- a path that never exists. So every non-rapid land's own composed-tree
check observes _land_commit_in_progress() == False, and
_testsuite_glob_growth_finding never auto-accepts/writes the ratchet
lock the way T-4563's own docstring says it will -- it just re-reports
the same pending SELFAUDIT001/SYS111 finding as a real, land-blocking
error every time, refusing the land in a loop with no path to green
(confirmed live: T-4508's land refused twice on this exact finding,
/tmp/land-T-4508.log).

Repro: land any ticket whose diff grows a testsuite bare-glob via-list
beyond its committed ratchet ceiling, on a non-rapid profile (warm-stage
sweep wired) -- SYS111 refuses every attempt.

Fix: pass the land's actual lock-holding root explicitly to the
composed-tree check spawn (an env var the spawned subprocess's
_land_commit_in_progress reads in preference to its own root argument),
not a path heuristic reconstructing the primary checkout from the
warm-stage's nested layout.
