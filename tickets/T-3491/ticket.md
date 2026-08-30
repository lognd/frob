---
id: T-3491
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-3486):
  1 new (rule, file) identit(ies), 1 finding(s) (DOC006)'
state: queued
kind: bug
origin: agent
created: '2026-08-30'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-3489/ticket.md
findings:
- - DOC006
  - tickets/T-3489/ticket.md
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
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-3486) at commit 4882181199964e3782579d3cd16a2b605405f1e2 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-3489/ticket.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-3489/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Failure log
- 2026-08-30 attempt 1: resolved on main by T-3489 landing: T-3489's own ticket.md is a queued-ticket body while open, and DOC006's frob.app.telemetry._state pointer fired then; T-3489 landed (state=done), and DOC006's existing _is_historical_ticket_doc/_terminal_ticket_ids exemption (T-2505/T-2374) already treats a DONE ticket's body as an immutable historical record, so the finding cleared automatically once state flipped -- no code change needed. Proof: pytest tests/test_docptr_gate.py::TestDoc004Doc006ZeroOnFrobsOwnRepo::test_doc004_doc006_zero_against_live_repo -p no:xdist -- 1 passed, 0 failed (run from t-3491 worktree at main tip after T-3489's land).
