---
id: T-2692
title: SELFAUDIT001 capability-ratchet debt in design/frob.strata (split from T-2303)
state: dropped
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- design
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
Split from T-2303: the `design` capability-ratchet half of that ticket's
findings (SELFAUDIT001 -- 2 undeclared capability effects in test files
plus fs.write via-list on core at 22 sites, above the committed ratchet
ceiling of 21, docs/design/registry/capability-via-ratchet.lock.json)
could not be worked as part of T-2303 because `design/frob.strata`
carries T-1656's LIVE cross-worktree lease -- `frob ticket start`
refused the collision outright. T-2303 itself proceeded scoped to only
its four Python source files (telemetry.py, _land_cmd.py, _new.py,
_rapid_sweep.py).

Re-measure the SELFAUDIT001 finding against current `main` before
starting this (it may already be affected by T-1656's own land), and
coordinate scope with whatever ticket holds `design/frob.strata` at
that time.

## Drop reason
- 2026-08-21: already resolved, measured 2026-08-21: the ratchet-ceiling half was raised core::fs.write 21->25 by T-2407 (landed 2026-08-19/20) and frob check --ticket T-2692 fires ZERO SYS111 findings; the '2 undeclared capability effects' half is not undeclared -- the only remaining SELFAUDIT001 findings are 2 pre-existing SYS107 WARNings (fs.read/fs.write via-less on the testsuite node) that already carry an explicit because= justification from T-2503's deliberate ambient-grant design, and are WARN not ERROR. gate:SELFAUDIT reports 0 errors, 2 warnings, 0 unresolved, 0 waived. Dropped rather than requeued because 'already resolved' returning to queued makes the ticket a treadmill for the next agent to rediscover. (absorbed by T-2407)
