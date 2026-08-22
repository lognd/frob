---
id: T-2538
title: 'post-land sweep regression from T-2523: 5 new (rule, file) identit(ies) (E501,
  F401)'
state: dropped
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- scripts/fleet_status.py
- src/frob/app/ticket_runner/_verify.py
- src/frob/graph/summary.py
- src/frob/testing/_collect_kotlin.py
- tests/unit/test_ticket_runner_repro_merge_base.py
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
The deferred post-land unscoped sweep (T-1684) for T-2523 at commit c44342c5cb0edcf99b06ca9c3935f8fecb981086 found 5 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- E501  /home/logan/projects/frob/scripts/fleet_status.py
- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_verify.py
- E501  /home/logan/projects/frob/src/frob/graph/summary.py
- E501  /home/logan/projects/frob/src/frob/testing/_collect_kotlin.py
- F401  /home/logan/projects/frob/tests/unit/test_ticket_runner_repro_merge_base.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  /home/logan/projects/frob/scripts/fleet_status.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_verify.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/graph/summary.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/testing/_collect_kotlin.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- F401  /home/logan/projects/frob/tests/unit/test_ticket_runner_repro_merge_base.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-18: sweep false positive: all 5 (rule,file) identities pre-existing at T-2523's parent commit bc41a659757f849dc6464d158161a9db95822f31, not introduced by T-2523's land (which touched only design/frob.strata, src/frob/gates/_sys_selfaudit.py, src/frob/gates/_waive.py, src/frob/strata/_effects.py, tests/test_gates.py, tests/unit/strata/test_effects.py -- none of the 5 flagged files). Measured directly: scripts/fleet_status.py (101 lines >88 chars), src/frob/app/ticket_runner/_verify.py (25), src/frob/graph/summary.py (32), src/frob/testing/_collect_kotlin.py (10) all already over line-length at parent; tests/unit/test_ticket_runner_repro_merge_base.py already has the unused 'from typani import Ok' import at parent (never referenced in file body). Attribution engine already independently answered UNATTRIBUTED for all 5 with empty candidate lists. Stale rolling-sweep-baseline false positive, matching the known class documented in the T-2467-adjacent trap.
