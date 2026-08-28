---
id: T-3227
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2878):
  2 new (rule, file) identit(ies), 1 finding(s) (CLAUDE001, OPAQUE001)'
state: done
kind: bug
origin: agent
created: '2026-08-28'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .claude/hooks/sync-claude-config.py
- src/frob/app/ticket_runner/_land_cmd.py
evidence_scope:
- tests/test_vet_capability.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_vet_capability.py::TestSymbolResolvedContainerAndPartialEvasions::test_functools_partial_wrapping_dangerous_op_resolves
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
findings:
- - CLAUDE001
  - .claude/hooks/sync-claude-config.py
- - OPAQUE001
  - src/frob/app/ticket_runner/_land_cmd.py
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2878) at commit bc439433a8d983ff49b2a9fa99a55e570f7b1500 found 2 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (2), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 2 identit(ies).

New (rule, file) identit(ies) filed here:

- CLAUDE001  .claude/hooks/sync-claude-config.py
- OPAQUE001  src/frob/app/ticket_runner/_land_cmd.py

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- CLAUDE001  .claude/hooks/sync-claude-config.py  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []
- OPAQUE001  src/frob/app/ticket_runner/_land_cmd.py  -> attributed to T-2941 (commit 388573487c82, already closed/dropped -- filed below) via src/frob/app/ticket_runner/_land_cmd.py::_doc005_checker

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.