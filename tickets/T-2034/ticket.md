---
id: T-2034
title: Auto-drop sweep write leaves root dirty when the commit fails (T-1983 drop
  path missing T-1841 discard)
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/_rapid_sweep.py
- tests/unit/test_rapid_sweep.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_rapid_sweep.py
  reason: test file for the fix
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_commit_failure_restores_root_to_clean_not_left_dirty
- tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_retry_after_commit_failure_does_not_duplicate_the_reason
- tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite::test_returns_true_on_first_success
- tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite::test_retries_then_succeeds
- tests/unit/test_rapid_sweep.py::TestCommitOrDiscardLedgerWrite::test_exhausted_retries_calls_discard_exactly_once_and_returns_false
- tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop::test_v2_store_restores_the_ticket_file_to_head
- tests/unit/test_rapid_sweep.py::TestDiscardUncommittedTicketDrop::test_v1_store_logs_and_leaves_root_alone
designated_repro_test: tests/unit/test_rapid_sweep.py::TestCloseResolvedSweepTickets::test_commit_failure_restores_root_to_clean_not_left_dirty
threat: null
component: null
anchor: false
anchor_reason: null
---
`src/frob/app/ticket_runner/_rapid_sweep.py::_maybe_drop_resolved_ticket`
(T-1983) writes the ticket's dropped state via `drop_ticket(root, ...)`
(mutating `tickets/<id>/ticket.md` on disk) and then attempts to commit it
via `commit_ticket_ledger_change`. If the commit fails -- routinely,
because a concurrent `frob ticket land` holds root's exclusive lock
(LeaseError.LandInProgress) -- the function logs an error and returns
None, LEAVING the modified ticket.md uncommitted in the shared root. Every
subsequent `frob ticket land` then refuses with `DirtyMain`.

MEASURED (coordinator, 2026-08-10): root observed dirty with exactly 6
modified `tickets/*/ticket.md` files with no land in flight (only a
wait-loop plus several concurrent `frob ticket doable` runs in `ps aux`).
`git checkout HEAD -- tickets/` cleaned it; it re-dirtied within ~60s with
no land running while `doable` runs were live -- consistent with
`_maybe_drop_resolved_ticket`'s write-then-commit-fails path, since
`doable` is a read path that would not itself dirty the tree, but the
DETACHED sweep this module drives runs after every land and is plausibly
what re-dirtied it.

Non-idempotency evidence: T-2000, T-2008, T-2022 each carried the SAME
auto-drop reason line TWICE in their ticket.md -- because the write was
never committed and never discarded, the next sweep still saw the ticket
as QUEUED (the commit never landed) and dropped it again, appending a
duplicate reason block on the next pass.

OBSERVED BUT UNATTRIBUTED (do not treat as this ticket's cause): the
coordinator also found `tickets/T-1998/ticket.md` and its
`done-report.md` modified, with `## Done report` REPLACED by `## Drop
reason` in the dirty copy (restored from HEAD, Done report content
confirmed intact). T-1998's committed state is `done`, and
`_close_resolved_sweep_tickets`'s scan only considers QUEUED/PLANNED
tickets, so this specific incident could NOT be attributed to this sweep
path by direct code reading. Recorded here for visibility only; not
claimed as caused by this defect.

## Precedent
T-1841 already established and shipped the fix for the sibling write path
in this SAME module (`_commit_regression_ticket` /
`_discard_uncommitted_regression_ticket`): "if the commit cannot succeed
... the sweep must NOT leave the file behind. Either write-then-commit
atomically or do not write." T-1983's newer auto-drop path
(`_maybe_drop_resolved_ticket`) never received the same treatment.

## Fix direction
1. Discard-on-commit-failure for the auto-drop path, mirroring
   `_discard_uncommitted_regression_ticket` -- but note the shape differs:
   the regression path writes a brand-new untracked `tickets/<id>/`
   directory (safe to `rmtree`), while the drop path MODIFIES an
   already-tracked, already-committed `ticket.md` (must be restored via
   `git checkout HEAD -- <path>`, never rmtree'd, or a real ticket's
   history is destroyed).
2. Prefer a single shared helper every sweep ledger write goes through, so
   the next write path added to this module inherits the guarantee
   instead of re-earning it.
3. A gate or test asserting a sweep write path cannot return with root
   dirty.

## Acceptance criteria
1. A test that FAILS FIRST: simulate `commit_ticket_ledger_change` failing
   (LandInProgress) during an auto-drop, and assert root is DIRTY today;
   then assert the fixed behavior leaves root CLEAN.
2. No duplicate reason lines: dropping the same ticket twice (once
   discarded, once retried) must not append two reason blocks.
3. The regression-ticket path (`_commit_regression_ticket`) keeps passing
   its existing tests unchanged (or is refactored onto the same shared
   helper with equivalent behavior).