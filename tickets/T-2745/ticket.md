---
id: T-2745
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2712):
  1 new (rule, file) identit(ies), 1 finding(s) (DOC006)'
state: done
kind: bug
origin: agent
created: '2026-08-20'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tickets/T-2742/ticket.md
- tests/unit/test_ticket_2691_doc006.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_2691_doc006.py
  reason: 'add T-2742 regression case to the existing DOC006 recurring-shape test
    file (same root cause as T-2691/T-2697: a backtick-quoted hypothetical CLI verb
    read as a real invocation) rather than fixing prose with no verifying evidence'
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: 'BUG002 is unsatisfiable by construction here: the fix is a ticket-body
    prose edit, not a code change, so no designated test can genuinely fail at parent
    and pass at fix (both would evaluate DOC006''s unchanged gate logic identically);
    documenting per T-1616/BUG002 escape-hatch guidance in docs/modules/gates.md'
  actor: logan
  at: '2026-08-20'
  old_length: 1192
  new_length: 1643
evidence:
- tests/unit/test_ticket_2691_doc006.py::TestTicket2742Doc006Regression::test_backticked_future_verb_is_flagged
- tests/unit/test_ticket_2691_doc006.py::TestTicket2742Doc006Regression::test_prose_description_of_future_verb_not_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 1c7c2a309dde2c45eb5c1303a07dffc9bf94f8fb
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2712) at commit 802534a13ec31014fcbdee9fed8224a2c0073228 found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC006  tickets/T-2742/ticket.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC006  tickets/T-2742/ticket.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="pure content/prose fix -- the defect was a hypothetical CLI verb quoted in backticks inside a ticket body (data, not code), so no code path or gate LOGIC changed for the designated evidence test to differentiate before/after; the added regression tests (TestTicket2742Doc006Regression) prove the FIXED shape does not trip DOC006 and the PRE-FIX shape still does, exercising the same gate logic T-2697/T-2691 already covers"