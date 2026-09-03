---
id: T-3090
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3039):
  2 new (rule, file) identit(ies), 1 finding(s) (DOC006, I001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/verify/test_quarantine.py
- tickets/T-3086/ticket.md
findings:
- - DOC006
  - tickets/T-3086/ticket.md
- - I001
  - /home/logan/projects/frob/tests/unit/verify/test_quarantine.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 69058fc5e4037847423487a25c9bf8f367b49c1a
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3039) at commit b99c0a9fa9be410b2439fec8ade5fd2bc9da6732 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-3086/ticket.md
- I001  /home/logan/projects/frob/tests/unit/verify/test_quarantine.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-3086/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- I001  /home/logan/projects/frob/tests/unit/verify/test_quarantine.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-28: Re-measured both identities against current main -- both stale. DOC006 tickets/T-3086/ticket.md: T-3086 closed+archived since this sweep filed; file no longer exists in a fresh worktree. I001 tests/unit/verify/test_quarantine.py: frob check --only ruff --skip-ruff-format across the full repo returns 0 errors/0 warnings, ruff-check 'no issues' -- no I001 finding anywhere. Both premises falsified; matches this drive's ~90% stale rate.
