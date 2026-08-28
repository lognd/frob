---
id: T-2881
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2871):
  1 new (rule, file) identit(ies), 3 finding(s) (DOC006)'
state: dropped
kind: bug
origin: agent
created: '2026-08-22'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2879/ticket.md
findings:
- - DOC006
  - tickets/T-2879/ticket.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 12101680cedcb2c6bb253ef7ed43b35c082c7d24
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2871) at commit a7c59979d639cd373c041f7ee45d63fd61a9c85f found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 3 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-2879/ticket.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-2879/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-25: stale-baseline false positive: the file this identity was filed against, tickets/T-2879/ticket.md, no longer exists at that path -- T-2879 was subsequently archived (commit 8d131b53a, 'archive 886 ticket(s)') and now lives at tickets/archive/T-2879/ticket.md. Re-measured 'frob check --only docblocks --json' on current main: zero DOC006 hits anywhere naming T-2879 (archived or active path). Nothing to fix; the routine archive move resolved this on its own.
