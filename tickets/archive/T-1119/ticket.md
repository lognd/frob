---
id: T-1119
title: 'gates: TICK006 phantom draft citations from T-1077/T-1084 Done reports'
state: dropped
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
---
frob check reports TICK006 phantom-filing-trail errors for T-1077 and
T-1084: both Done reports cited draft ids (since repaired by the
coordinator in 0abc4e3a) as
filed follow-on tickets, but neither draft resolved to a real block in
tickets.md or tickets-archive.md -- the classic T-0707/T-0615 draft-loss
incident class (a worktree's draft ticket getting wiped by the section
10b tickets.md restore recipe before the citing Done report landed).
Found incidentally while landing T-1095 (unrelated ticket); not this
ticket's scope to fix. Resolve by either re-filing the real ticket each
Done report meant to cite and correcting the citation, or adding an
honest frob:waive TICK006 noting the historical draft loss if the
underlying work is otherwise already covered.

## Drop reason
- 2026-07-28: moot: the T-1077/T-1084 TICK006 phantom citations were repaired inline by the coordinator (0abc4e3a: T-1115 refile + T-1112 repoint) before this ticket landed