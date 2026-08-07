---
id: T-1779
title: 'Nothing guards the root checkout against a coordinator writing during a land:
  five stalls and one corrupted ticket state'
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/app/ticket_runner/__init__.py
- src/frob/tickets/_leases.py
- src/frob/app/worktree_runner.py
- docs/modules/tickets.md
- tests/test_ticket_leases.py
- tickets/T-1779/ticket.md
- tickets/T-1786/ticket.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_ticket_leases.py
  reason: unit tests for remove_worktree and the new dispatch-level land-in-progress
    guard belong beside the existing TestSweepWorktrees/TestRefuseIfLandInProgress
    classes in this file
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1779/ticket.md
  reason: v2-store per-ticket ledger files for this ticket itself and its own follow-up
    draft -- same LEDGER_PATH-only-covers-legacy-tickets.md gap T-1613 hit
  actor: logan
  at: '2026-08-07'
- op: add
  glob: tickets/T-1786/ticket.md
  reason: v2-store per-ticket ledger files for this ticket itself and its own follow-up
    draft -- same LEDGER_PATH-only-covers-legacy-tickets.md gap T-1613 hit
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001/SYS104: the cli and tickets_ledger design nodes'' interface
    lists must declare _refuse_if_land_in_progress_for_dispatch and remove_worktree
    respectively'
  actor: logan
  at: '2026-08-07'
evidence:
- tests/test_ticket_leases.py::TestWorktreeRemoveCli::test_remove_cli_removes_a_clean_unleased_worktree
- tests/test_ticket_leases.py::TestWorktreeRemoveCli::test_remove_cli_exits_1_and_names_the_error_for_a_bad_path
- tests/test_ticket_leases.py::TestWorktreeRemoveCli::test_remove_cli_exits_1_when_kept
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_read_only_verb_runs_while_land_in_progress
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all
- tests/test_ticket_leases.py::TestDispatchLandGuard::test_land_verb_itself_is_exempt
- tests/test_ticket_leases.py::TestRemoveWorktree::test_removes_a_clean_unleased_worktree
- tests/test_ticket_leases.py::TestRemoveWorktree::test_keeps_a_live_process_worktree
- tests/test_ticket_leases.py::TestRemoveWorktree::test_refuses_a_path_not_registered_as_a_worktree
designated_repro_test: null
threat: null
component: null
---
A coordinator with write access to the root checkout can corrupt an
in-flight land, and nothing stops it. This has cost the fleet FIVE
separate stalls in one session and corrupted one ticket's state.

Every agent is correctly sandboxed to its own worktree and cannot touch
root. The coordinator is not sandboxed at all, and is the only actor that
writes to root while lands are running. The guards that exist all point
the wrong way: they protect root FROM agents, and agents from each other.

THE FIVE INCIDENTS, all mine:

1. Uncommitted development work in root DirtyMain-blocked every agent's
   land. Three agents burned their remaining budget diagnosing it; none
   could see root to find the cause.
2. A bare `git commit` (correctly-scoped `git add`, no pathspec on the
   commit) took the WHOLE INDEX and published 1416 lines of another
   agent's in-flight T-1688 work under an unrelated chore message. That
   commit also moved root's tip, blocking the same agent for an hour on
   drift it could not diagnose.
3. A staged `git rm -r agents skills` left in root refused another
   agent's land with DirtyMain.
4. `git worktree remove` deleted a LIVE agent's checkout. Its branch
   survived only because it had committed; the guard added that same day
   (T-1739) protects `frob worktree sweep`, not raw git.
5. `frob ticket close` for two tickets ran WHILE a land was mid-flight.
   The commits landed between that land's pre-land snapshot and its
   staging step. T-0907 correctly refused the land -- but the ledger had
   already been written and the source had not, leaving T-1678 reading
   `done` on main with its code absent and two COV003 findings against
   evidence naming tests that did not exist. A ticket claiming completion
   for work that is not there is the most damaging state this ledger can
   hold, because every downstream reader trusts it.

THE FIX ALREADY EXISTS AND IS SCOPED TOO NARROWLY. Incident 5 ended when
`frob ticket done-report`/`close` began refusing with `LandInProgress:
a land is in progress for this repository; retry after it completes`.
That guard is exactly right and it is why the damage stopped. It just
does not cover the other four shapes.

REQUIRED:

1. Extend the `LandInProgress` refusal to EVERY ledger-mutating verb, not
   only the closeout family. `new`, `scope`, `evidence`, `block`,
   `priority`, `start`, `archive` and the rest all write the ledger a
   land is mid-way through reading and rewriting.
2. A pre-flight guard on `frob ticket land` itself: refuse to START a
   land when root's index already holds staged content the land did not
   put there, naming the paths. T-1740 fixed land LEAVING staged residue;
   this is the mirror -- refusing to begin on top of someone else's.
3. `git worktree remove` cannot be guarded, but `frob worktree` can grow
   a `remove` verb that performs the liveness check T-1739 already built
   for `sweep`, so there is a safe path that is easier to reach than the
   raw command.
4. Consider making the land lock advisory-visible to a human: a
   `frob doctor`-style line, or a marker file whose presence a
   coordinator can check before doing anything in root. Right now the
   only way to know is `pgrep`, which is not discoverable.

WHAT THIS TICKET IS NOT: more coordinator discipline. Discipline was the
control in every one of the five incidents and it failed every time,
including immediately after writing the rule down. Two of the five
happened AFTER filing tickets about the previous ones. The lesson this
repo keeps relearning is that a rule which lives only in prose protects
nothing -- it is the same finding as INV006's 338 waivers, T-1733's
silent evidence unbinding, and the `--force` family that logged nothing.

Sibling: T-1613 landed a `runs-last` marker for exactly this class of
"must be alone" operation. The archive and migration incidents it was
filed for are the same shape as these five. Where a coordinator operation
genuinely needs exclusivity, `runs-last` is now the mechanism -- but it
gates TICKETS, and incidents 1-4 were raw git, which no ticket gates.