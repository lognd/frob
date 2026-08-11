---
id: T-2085
title: 'post-land sweep regression from T-2076: 2 new (rule, file) identit(ies), 5
  finding(s) (ARCH001, CLAUDE001)'
state: queued
kind: bug
origin: agent
created: '2026-08-10'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- .claude/hooks/sync-claude-config.py
- src/frob/tickets/_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-2076 at commit 8215a988f8425c2e20ff484f25d99bf498893f69 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 5 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- ARCH001  src/frob/tickets/_land.py
- CLAUDE001  .claude/hooks/sync-claude-config.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- ARCH001  src/frob/tickets/_land.py  -> UNATTRIBUTED (2 batch commits' touched symbols all reach this finding); candidate commits: ['27f893f7b196186b4be542137f0386a8703701fd', '062a9877a58b2a0fe1bb1a6b24226cffd40468db']
- CLAUDE001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.