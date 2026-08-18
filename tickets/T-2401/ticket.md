---
id: T-2401
title: 'post-land sweep regression from T-2387, T-2385, T-2386: 1 new (rule, file)
  identit(ies) (CLAUDE001)'
state: dropped
kind: bug
origin: agent
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/sync-claude-config.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-2387, T-2385, T-2386 at commit 21c4ceedcd5770d5f77d9cfffcdf4d26c3abbfed found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES, not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). The true per-finding count could not be independently re-measured this run (spawn refused/timeout/unparsable) -- re-run `frob check` unscoped against the file(s) below for the exact count before treating this identity count as a completeness claim.

New (rule, file) identit(ies) filed here:

- CLAUDE001  .claude/hooks/sync-claude-config.py

T-2009: 3 lands (T-2387, T-2385, T-2386) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-2387, T-2385, T-2386 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- CLAUDE001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-18: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (CLAUDE001 .claude/hooks/sync-claude-config.py) is absent from the fresh unscoped measurement at T-2392's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
