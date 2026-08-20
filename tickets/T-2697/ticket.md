---
id: T-2697
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-1549):
  1 new (rule, file) identit(ies), 1 finding(s) (DOC006)'
state: done
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
- tickets/T-2691/ticket.md
- tests/unit/test_ticket_2691_doc006.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_2691_doc006.py
  reason: regression test proving the T-2697 DOC006 fix in tickets/T-2691/ticket.md
  actor: logan
  at: '2026-08-20'
evidence:
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_prose_description_of_future_verb_not_flagged
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_real_ticket_file_not_flagged
designated_repro_test: tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_real_ticket_file_not_flagged
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: e213366d39d9316af19db88d1421a00ee6d9a3a3
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-1549) at commit 8a27d7828799b26ced7a8677ee820c533dcb67eb found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-2691/ticket.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-2691/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.