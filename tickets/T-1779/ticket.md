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

## Done report

Closed gap 1 and gap 3 of T-1779's four requirements; confirmed gap 2
already existed; gap 4 disclosed as a follow-up (T-1786).

GAP 1 -- extended LandInProgress to every ledger-mutating verb, and
critically, moved the refusal to BEFORE the write, not merely before the
commit. The pre-existing `refuse_if_land_in_progress` guard lived only
inside `_add_and_commit_tickets_md` (the COMMIT half), so a mutating
verb's handler already ran to completion -- writing its change to the
working tree via `write_ticket` -- before that check could refuse
anything. `frob.app.ticket_runner._refuse_if_land_in_progress_for_dispatch`
now runs BEFORE `handler(root, cfg)`, wrapping the single dispatch call
site in `run()` (the same T-1615 "one choke point" shape
`_auto_commit_ledger_after_dispatch` already established), with two
explicit sets: `_LAND_SAFE_READ_ONLY_VERBS` (list/show/doable/board/epic/
brief/flow -- a coordinator can still inspect state during a land) and
`_LAND_LOCK_EXEMPT_VERBS` (land/merge-driver/sweep-async -- land holds
the lock itself, merge-driver runs as land's own subprocess and would
deadlock against itself if gated, sweep-async owns its own T-1699
interaction).

Incident 6 (reported live mid-ticket) proved this "before the write, not
before the commit" distinction was not academic: `frob ticket runs-last
T-1780 on` printed "runs-last now True" and only THEN failed the commit
with LandInProgress -- a partial write. A new test,
`test_refused_verb_never_writes_the_ticket_file_at_all`, reproduces
exactly that shape (a real `frob ticket runs-last` CLI call while a real
`_land_lock` is held) and asserts the on-disk field is UNCHANGED, not
merely uncommitted -- proving the pre-dispatch guard actually closes it.

Incident 6 also surfaced a SEPARATE bug already ticketed: `frob ticket
new` itself left an untracked `tickets/T-1780/` directory (new_ticket has
no auto-commit of its own -- T-1615's uniform auto-commit wraps the CLI
dispatch layer, not the library call underneath it), which later
DirtyMain-blocked an unrelated land. That is T-1758's scope
(_new_renumber.py/_leases.py/_store.py), not this ticket's -- cross-
referenced explicitly in docs/modules/tickets.md's new section, since the
two are two halves of one fix and landing only one leaves the hole open.

GAP 2 -- verified already closed, no new code. `_land_precheck` (the
first thing `_land_locked` runs, before ANY of land's own staging) already
calls `_refuse_if_main_dirty`, and `describe_root_dirt`'s T-1740 callout
already names STAGED paths specifically ("N STAGED (likely a prior
land's leftover index, T-1740)"). Verified directly against incident 3:
a staged `git rm -r agents skills` left in root DID refuse the next land
with DirtyMain, naming the staged paths -- the guard worked as designed;
the incident's cost was diagnosis time, not a guard failure.

GAP 3 -- `frob.tickets._leases.remove_worktree(root, path, *,
dry_run=False, force=False)`: the single-worktree twin of
`sweep_worktrees`, reusing `_sweep_verdict_for_worktree` directly for
exactly one candidate so the same T-1739 liveness-first gate, clean/
lease/age gates, and `force` escape hatch apply unchanged.
`Err(NotARegisteredWorktree)` if the target is not one of root's own
git-registered `.claude/worktrees/` agent worktrees. `frob worktree
remove PATH [--dry-run] [--force]` (`frob.app.worktree_runner`) is the
CLI surface -- same subcommand family as `sweep`, one new argparse
subparser.

GAP 4 -- disclosed as a follow-up rather than half-built:
T-1786 ("Give the land lock a discoverable, side-effect-free
visibility surface") for a `frob doctor`-style line. The underlying
primitive (`refuse_if_land_in_progress`) already exists; this is a read
surface for it, not built in this pass.

Scope extended file-by-file with --reason as each dependency surfaced
(design/frob.strata for SELFAUDIT001/SYS104's interface-list requirement
on both new public symbols; the v2-store per-ticket ledger/done-report
files for this ticket and its own follow-up draft, the same
LEDGER_PATH-only-covers-legacy-tickets.md gap T-1613 hit; tests/
test_ticket_leases.py for the new test coverage) -- never a mega-glob.

`frob check --only prework --only scope --only sys --ticket T-1779` is
clean. `frob check --land-parity` is clean. `frob check --only coverage`
shows 0 new COV002/COV007 findings for any touched symbol.

### Changed
```
 tickets/T-1779/ticket.md           | 44 +++++++++++++++++++++++++++++++++++++-
 tickets/T-1786/ticket.md | 34 +++++++++++++++++++++++++++++
 2 files changed, 77 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/test_ticket_leases.py::TestWorktreeRemoveCli::test_remove_cli_removes_a_clean_unleased_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeRemoveCli::test_remove_cli_exits_1_and_names_the_error_for_a_bad_path` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestWorktreeRemoveCli::test_remove_cli_exits_1_when_kept` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_refuses_mutating_verb_while_land_in_progress` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_read_only_verb_runs_while_land_in_progress` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_refused_verb_never_writes_the_ticket_file_at_all` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestDispatchLandGuard::test_land_verb_itself_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRemoveWorktree::test_removes_a_clean_unleased_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRemoveWorktree::test_keeps_a_live_process_worktree` (pytest node id, verified passing when recorded)
- `tests/test_ticket_leases.py::TestRemoveWorktree::test_refuses_a_path_not_registered_as_a_worktree` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: 1 error(s), 970 warning(s), 723 waived
- error-findings: AFFECT001@src/frob/app/worktree_runner.py
