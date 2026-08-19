---
id: T-2597
title: 'post-land sweep regression from T-2588: 2 new (rule, file) identit(ies), 0
  finding(s) (E501)'
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
- src/frob/app/ticket_runner/_ledger_mirror.py
- src/frob/scaffold/project.py
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
The deferred post-land unscoped sweep (T-1684) for T-2588 at commit 18de7953cf1fa64e7fb21345b15dfe422557b0c2 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 0 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_ledger_mirror.py
- E501  /home/logan/projects/frob/src/frob/scaffold/project.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- E501  /home/logan/projects/frob/src/frob/app/ticket_runner/_ledger_mirror.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- E501  /home/logan/projects/frob/src/frob/scaffold/project.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-19: FALSE POSITIVE, confirmed by two independent checks: (1) blamed-land T-2588 commit 18de7953cf1fa64e7fb21345b15dfe422557b0c2 touches CHANGELOG.md/changelog.d/rapid-debt.jsonl/cycle_runner.py/two test files/tickets ledger files -- NEITHER of the 2 flagged files (_ledger_mirror.py, scaffold/project.py); (2) frob check --only ruff --json on current main reports ZERO E501 findings repo-wide (only I001 exists), matching the tickets own filed-time disclosure of 0 finding(s). Filed 2026-08-19 01:37, AFTER T-2571 (01:31) but BEFORE T-2595 (03:27) -- the false-attribution mechanism T-2571 targeted (phantom findings against deleted paths) is a different defect than the one causing this E501 class; T-2571 landing did not prevent this specific false positive.
