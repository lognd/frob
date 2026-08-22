---
id: T-2643
title: 'post-land sweep regression from T-2606: 2 new (rule, file) identit(ies), 0
  finding(s) (F401, TICK006)'
state: dropped
kind: bug
origin: agent
created: '2026-08-19'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/__init__.py
- tickets.md
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
The deferred post-land unscoped sweep (T-1684) for T-2606 at commit 9f0c8562e924b4f168410f3eaa3fc0b013015562 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- F401  /home/logan/projects/frob/src/frob/app/ticket_runner/__init__.py
- TICK006  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- F401  /home/logan/projects/frob/src/frob/app/ticket_runner/__init__.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TICK006  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-19: FALSE POSITIVE, confirmed by two independent checks: (1) blamed-land T-2606 commit 9f0c8562e924b4f168410f3eaa3fc0b013015562 touches CHANGELOG.md/changelog.d/check-coverage.yaml/rapid-debt.jsonl/_waive.py/test_waive_gate.py/tickets ledger files -- NEITHER of the 2 flagged files (ticket_runner/__init__.py, tickets.md); (2) frob check --json full unscoped run on current main reports ZERO F401 findings and ZERO TICK006 findings repo-wide, matching the tickets own filed-time disclosure of 0 finding(s). Filed 2026-08-19 06:16, AFTER both T-2571 (01:31) and T-2595 (03:27) fixes -- so this is a DIFFERENT false-positive mechanism than either of those two targeted, worth noting to the coordinator, not evidence either fix regressed (blamed-land-did-not-touch-file is the same root shape both times, not something either fix was designed to catch).
