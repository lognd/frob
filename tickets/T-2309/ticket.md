---
id: T-2309
title: 'post-land sweep regression from T-2164: 1 new (rule, file) identit(ies), 1
  finding(s) ()'
state: dropped
kind: bug
origin: agent
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
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
The deferred post-land unscoped sweep (T-1684) for T-2164 at commit eadd8c7d8675239bb76b0c51ab3a66a1be1d5fb9 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

-   

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

-     -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-17: blank (rule, file) identity: ledger body's 'New identit(ies) filed here' bullet and attribution line are both empty (no rule, no file, empty candidate list) -- the degenerate sweep-filer artifact matching T-2326/T-2332, already fixed at source by T-2345 and at the choke point by T-2313. No real regression to fix.
