---
id: T-1859
title: 'post-land sweep regression from T-1857: 8 new error(s) (COV001, TEST001)'
state: queued
kind: bug
origin: agent
created: '2026-08-08'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/_shellscan.py
- .claude/hooks/diagnosis-nudge.py
- .claude/hooks/dispatch-telemetry.py
- .claude/hooks/frob-suggest.py
- .claude/hooks/frob-timeout-guard.py
- .claude/hooks/sync-claude-config.py
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
The deferred post-land unscoped sweep (T-1684) for T-1857 at commit 87298c57f9e354e2af84a45b171b9535ab1da2b5 found 8 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- COV001  .claude/hooks/_shellscan.py
- COV001  .claude/hooks/diagnosis-nudge.py
- COV001  .claude/hooks/dispatch-telemetry.py
- COV001  .claude/hooks/frob-suggest.py
- COV001  .claude/hooks/frob-timeout-guard.py
- COV001  .claude/hooks/sync-claude-config.py
- COV001  design/frob.strata
- TEST001  .claude/hooks/_shellscan.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- COV001  .claude/hooks/_shellscan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  .claude/hooks/diagnosis-nudge.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  .claude/hooks/dispatch-telemetry.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  .claude/hooks/frob-suggest.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  .claude/hooks/frob-timeout-guard.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- COV001  design/frob.strata  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- TEST001  .claude/hooks/_shellscan.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.