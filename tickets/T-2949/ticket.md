---
id: T-2949
title: 'frob ticket land --finish: ''already done'' check reads uncommitted working-tree
  state, not main''s HEAD -- can delete a worktree before the real land happens'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land_finalize.py
- tests/unit/test_land_finish_idempotent.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_land_finish_idempotent.py
  reason: BUG002 repro + must-fire/must-stay-quiet fixtures for the git-HEAD-only
    ticket-state read
  actor: logan
  at: '2026-08-28'
evidence:
- tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_done_ticket_returns_its_state
- tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_done_ticket_uncommitted_on_disk_returns_none
- tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_in_progress_ticket_returns_none
- tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_unknown_ticket_id_returns_none
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_terminal_on_main_skips_land_core_and_cleans_up
- tests/unit/test_land_finish_idempotent.py::TestFinishOnlyIfAlreadyLanded::test_non_terminal_on_main_runs_the_normal_land
- tests/unit/test_land_finish_idempotent.py::TestReadTicketStateAtHead::test_reads_committed_state_not_dirty_working_tree
- tests/unit/test_land_finish_idempotent.py::TestReadTicketStateAtHead::test_returns_none_when_head_has_no_such_ticket
designated_repro_test: tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_done_ticket_uncommitted_on_disk_returns_none
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reproduced directly this session (T-2927, immediately after the T-2927
land attempt hit a concurrent-drift abort -- "refused to unwind ... drift
detected mid-staging, T-0907" -- which correctly left the working tree
unstaged and uncommitted, per its own docstring's safety guarantee):

Re-running `frob ticket land T-2927 --worktree <wt> --finish` immediately
after that abort printed:

    ticket land --finish: T-2927 is already 'done' on main -- skipping a
    full re-land (T-2108: a prior land already succeeded, or the ticket
    was closed directly) and running pure cleanup only
    ticket land --finish: T-2927 removed worktree <wt>

...and removed the worktree. But T-2927 was NOT actually committed to
main: `git show HEAD:tickets/T-2927/ticket.md` still read `state: queued`
at that exact moment, and the ticket's real land commit did not exist on
main's ancestry at all (only on the now-orphaned worktree branch). The
"already done" check apparently read the WORKING TREE's `tickets/T-2927/
ticket.md` (which still had `state: done` as leftover uncommitted content
from the aborted land's own pre-commit staging) rather than checking
whether that state was actually reachable from `main`'s HEAD.

Net effect: the worktree was deleted while the ticket's real land had NOT
happened, and the only remaining copy of the finished work was the
about-to-be-orphaned branch (`t-2911-series` in this instance) -- had that
branch also been swept/deleted before anyone noticed, the ticket's
evidence and Done report would have been lost outright, the exact T-1636
shape the playbook already warns about for a different code path.

Recovery performed by hand (not by the tool): verified the dirty root's
uncommitted content was byte-identical to what the orphaned branch already
had committed, discarded the root's dirty working tree (`git checkout --`/
`git clean -f` on exactly those paths, after confirming zero content
loss), re-created a worktree from the intact branch, rebuilt natives (the
recreated worktree had none), and re-ran `frob ticket land` for real --
which this time genuinely committed T-2927 to main
(`5b9de4b423d931aa18baf9425c8873b2ec090157`, confirmed
`is_ancestor_of_main=True`).

Suggested fix direction (not implemented here -- `_land_finalize.py`/
`_land_cmd.py`'s `--finish` "already done" fast-path is out of this
ticket's scope): the "is this ticket already done" check that gates
skipping a full re-land must verify the state is reachable from `main`'s
actual HEAD (e.g. `git show main:tickets/<id>/ticket.md`, or an
ancestry check against the commit that set `state: done`), never the
working tree's on-disk file content, which can carry a still-uncommitted
in-progress land's own intermediate state.