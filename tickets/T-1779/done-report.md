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
