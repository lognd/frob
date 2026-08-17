---
id: T-2190
title: 'post-land sweep regression from T-1780, T-2167: 2 new (rule, file) identit(ies),
  6 finding(s) (CLAUDE001, DOC011)'
state: dropped
kind: bug
origin: agent
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/sync-claude-config.py
- docs/design/gate-semantics-classification.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for T-1780, T-2167 at commit 5edb30a658f56b468fa484c19e0303e4b2b8dc4d found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 6 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- CLAUDE001  .claude/hooks/sync-claude-config.py
- DOC011  docs/design/gate-semantics-classification.md

T-2009: 2 lands (T-1780, T-2167) landed between the previous sweep's baseline and the commit THIS sweep actually measured (the sweep is deliberately detached, off the land critical path -- T-1684 -- so other agents' lands can land in the window before it runs). Which specific land introduced which finding below could not be determined without re-measuring at each intermediate commit; this ticket is filed against all of them rather than falsely pinned on T-1780, T-2167 alone (the one that happened to spawn this sweep process).

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- CLAUDE001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- DOC011  docs/design/gate-semantics-classification.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Drop reason
- 2026-08-17: T-1983: auto-dropped by the deferred post-land sweep -- every (rule, file) identity this ticket named (CLAUDE001 .claude/hooks/sync-claude-config.py, DOC011 docs/design/gate-semantics-classification.md) is absent from the fresh unscoped measurement at T-2112's deferred sweep, i.e. no longer reproduces. If this is wrong (a flaky/incomplete measurement), re-file with `frob check --only <gate>` evidence attached.
