---
id: T-2563
title: ledger-only ticket edits from a worktree strand on the branch and never reach
  main
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/
- tests/unit/test_ticket_runner_ledger_mirror.py
- docs/modules/tickets-lifecycle.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_ledger_mirror.py
  reason: the positive controls for the mirror live here
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-lifecycle.md
  reason: the mirror's public surface needs a documented anchor for its frob:doc edges
  actor: logan
  at: '2026-08-18'
evidence:
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_scope_edit_from_worktree_is_visible_on_primary
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_block_edit_from_worktree_is_visible_on_primary
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_attachment_file_reaches_primary
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorCarriesNothingElse::test_worktree_source_changes_do_not_leak_to_primary
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorCarriesNothingElse::test_primary_worktree_is_left_clean
- tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorScope::test_running_in_the_primary_checkout_is_a_no_op
designated_repro_test: tests/unit/test_ticket_runner_ledger_mirror.py::TestLedgerMirrorReachesMain::test_scope_edit_from_worktree_is_visible_on_primary
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: b8b4fddaafe70a3d652f294ed94dea6947361876
---
MEASURED 2026-08-18 by the agent working T-2377/T-2543.

`frob ticket scope`, `frob ticket block`, and `frob ticket attach` run
from inside a worktree AUTO-COMMIT their ledger edit to the WORKTREE
BRANCH. That commit reaches `main` only if a subsequent `frob ticket
land` happens to carry it. For a ticket whose work is not landing yet --
a decision ticket, a re-scope, a blocker edge, an attached analysis --
the edit never arrives.

CONCRETE INSTANCE: three T-2377 bookkeeping fixes (scope, blocked_by,
and an attachment) all reported SUCCESS from the worktree and were
INVISIBLE on main. They were recovered only because the agent thought to
verify against main afterwards, and had to be cherry-picked across by
hand (8b00bee7f, ade879967, f4da1e843).

THIS IS THE SILENT-ZERO FAMILY AGAIN, in its most deceptive form yet:
the command's success message is TRUE -- the commit really was made --
and the effect is simply unreachable from where anyone will look. There
is no error, no warning, and no way to notice except by independently
querying main.

RELATED INSTANCE, same day, different agent: T-2374's `blocked_by`
edge was recorded in its worktree ledger only, so `main` carried no
indication that the work existed or why it had stopped. That work sat
finished-and-unlanded for hours partly because of this.

WHY IT MATTERS BEYOND BOOKKEEPING: scope is a WRITE LEASE in this repo.
A `frob ticket scope --add` that lands only on a worktree branch means
the fleet's view of who holds which files is wrong -- the coordinator and
every other agent read main. A lease narrowing or widening that nobody
else can see is worse than not making it.

DELIVERABLE -- decide which, do not do all three:
1. Ledger-only mutations (scope/block/attach/priority/kind/etc -- verbs
   that touch ONLY tickets/ and no source) commit directly against main
   rather than the worktree branch, the way `frob ticket new` already
   manages to file a ticket visible to everyone.
2. Or: they refuse when run from a worktree, naming the correct
   invocation.
3. Or, weakest and least preferred: they SUCCEED but WARN loudly that
   the edit is worktree-local and will not be visible until the ticket
   lands.

Option 1 is preferred -- it removes the failure rather than reporting it.
Option 3 alone is not sufficient: an agent that reads the warning still
has no mechanism to get the edit to main short of a hand cherry-pick,
which is what happened today.

Note the constraint that makes this non-trivial: writing to main from a
worktree must not dirty the shared root while another land is staging
content there, and must not collide with the allocator/ledger locks.
`frob ticket new` already solves a version of this problem; look at how
before inventing a new mechanism.

POSITIVE CONTROLS, BOTH DIRECTIONS:
- a scope/block/attach issued from a worktree must be visible in main's
  ledger immediately afterwards (query main, not the worktree);
- a ticket whose SOURCE changes are still worktree-local must NOT have
  those source changes leak to main as a side effect -- only the ledger
  edit crosses;
- concurrent lands must not be dirtied or DirtyMain-blocked by the write.