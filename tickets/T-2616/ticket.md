---
id: T-2616
title: milestone missing from MIRRORED_LEDGER_VERBS; 4 verbs unclassified in dispatch-table
  accounting test
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_leases.py
- src/frob/app/ticket_runner/_ledger_mirror.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_milestone_edit_from_worktree_is_visible_on_primary
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_dispatch_table_verbs_are_all_accounted_for
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[reopen]
- tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::test_verb_leaves_repo_clean[milestone]
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2603 (ledger-write-pattern unification design pass).

`tests/test_ticket_leases.py::TestLedgerAutoCommitEnumeratedOverDispatchTable::
test_dispatch_table_verbs_are_all_accounted_for` is RED on unmodified main:
it enumerates `_ticket_dispatch_table()`'s real keys and fails if any verb
is not classified into one of _MUTATING_VERB_INVOCATIONS/_READ_ONLY_VERBS/
_NEEDS_DEDICATED_FIXTURE/_LEDGER_TRANSACTIONAL_VERBS. Four verbs added
since this test was last updated are unclassified:
`['body', 'contention', 'milestone', 'waive-audit']`.

Investigated each (as part of T-2603's own design pass, not fixed here
since this test file is outside T-2603's declared scope):

- `contention` (T-2395): pure read (`load_queue` + render), same shape as
  `wave` -> belongs in `_READ_ONLY_VERBS`.
- `waive-audit` (T-2467/T-2485/T-2496): `scan` renders a report,
  `complete` writes a WATERMARK file via `complete_pass`, never
  `tickets.md`/`write_ticket` -> belongs in `_READ_ONLY_VERBS` (read-only
  w.r.t. the ticket ledger specifically, even though `complete` has a
  side effect elsewhere).
- `body` (T-2392): already correctly a `MIRRORED_LEDGER_VERBS` member in
  `frob.app.ticket_runner._ledger_mirror` -> belongs in
  `_MUTATING_VERB_INVOCATIONS` here, just never added to this test.
- `milestone` (T-2574): `_milestone` -> `frob.tickets.set_milestone` ->
  `_set_ticket_field`, the SAME primitive `set_priority`/`set_kind`/
  `set_runs_last` use (all three ARE `MIRRORED_LEDGER_VERBS` members).
  `milestone` is MISSING from `MIRRORED_LEDGER_VERBS` -- this is not just
  a test-classification gap, it is a live T-2563-class bug: a worktree
  agent's `frob ticket milestone <id> <value>` commits locally but is
  never mirrored to the primary checkout, so the fleet cannot see it
  until the ticket lands. Same failure shape as the T-2377 incidents
  `_ledger_mirror.py`'s own module docstring describes.

Fix: add `contention`/`waive-audit` to `_READ_ONLY_VERBS`, `body` to
`_MUTATING_VERB_INVOCATIONS` (tests/test_ticket_leases.py), and add
`milestone` to `MIRRORED_LEDGER_VERBS`
(src/frob/app/ticket_runner/_ledger_mirror.py) with a regression test
proving a worktree `milestone` write is visible on the primary checkout
without a land, mirroring `TestPromoteMirror::test_promote_from_worktree_
is_visible_on_primary_without_a_land`'s shape.