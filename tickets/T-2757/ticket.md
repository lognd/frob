---
id: T-2757
title: 'post-land sweep regression from an unattributed source (sweep spawned by T-2741):
  1 new (rule, file) identit(ies), 1 finding(s) (DOC011)'
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
- docs/modules/tickets-verify-sweep.md
- tests/unit/gates/test_doc011.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/gates/test_doc011.py
  reason: add T-2757 regression cases to the existing DOC011 test file (a bare-vs-code-span
    ticket-id-mention shape) rather than fixing prose with no verifying evidence
  actor: logan
  at: '2026-08-20'
body_changes:
- mode: append
  reason: 'BUG002 is unsatisfiable by construction here per T-1616''s documented escape
    hatch: the fix is a doc-body backtick-quoting edit, not a code change, so no designated
    test can genuinely fail-at-parent/pass-at-fix (DOC011''s gate logic never changed,
    only doc DATA did)'
  actor: logan
  at: '2026-08-20'
  old_length: 1216
  new_length: 1654
evidence:
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_t2757_bare_mention_of_a_deliberately_nonexistent_id_is_flagged
- tests/unit/gates/test_doc011.py::TestDoc011TicketIdProse::test_t2757_fix_backtick_quoting_the_second_mention_clears_it
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
The deferred post-land unscoped sweep (T-1684) for an unattributed source (sweep spawned by T-2741) at commit 79c9e4a436160f20b1c1f7712b676ec450784e0e found 1 new (rule, file) identit(ies) that were not present in the previous sweep's baseline.

T-1935: this is a count of DISTINCT (rule, file) IDENTITIES (1), not a raw finding count -- every finding sharing a (rule, file) pair collapses into ONE identity here (deliberately, so attribution and quarantine reason about "which files went red", not individual diagnostics). An independent re-measurement found 1 actual finding(s) across those 1 identit(ies).

New (rule, file) identit(ies) filed here:

- DOC011  docs/modules/tickets-verify-sweep.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- DOC011  docs/modules/tickets-verify-sweep.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="pure content/prose fix -- the defect was a bare, non-code-spanned second mention of a phantom ticket id (T-2736) in doc prose (data, not code), so DOC011 gate LOGIC is unchanged before/after; the added regression tests (TestDoc011TicketIdProse::test_t2757_*) prove the pre-fix bare shape fires and the post-fix backtick-quoted shape does not, exercising the same gate logic the T-1542 precedent already covers"