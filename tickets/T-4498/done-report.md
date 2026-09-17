## Done report

T-4498 -- land's merge-dev step silently drops capability declarations
========================================================================

Problem (measured incident, T-4492's land):
  worktree commit 0294ab436 added a via-list entry to design/frob.strata
  (testsuite exec + fs.write) and bumped
  docs/design/registry/capability-via-ratchet.lock.json (307->308,
  521->522). The land's "merge dev into worktree for landing T-4492"
  commit (afcd60105) resolved BOTH files to dev's side (T-4491 had edited
  the same lines) with zero conflict reported -- the worktree's edit was
  discarded with no trace, and the land only failed later because the
  self-audit re-checked the SELFAUDIT001 findings the dropped edit itself
  declared.

Root cause found (src/frob/tickets/_land_git_ops.py):
  `_merge_main_into_worktree` runs `git merge --no-commit` and then
  `_check_only_tickets_conflicted` -> `_auto_resolve_out_of_scope_
  conflicts(cwd, ticket, keep="theirs")`. That function's job is
  legitimate for an ORDINARY file the landing ticket never declared in
  scope: a conflict there is noise from an unrelated main change, so
  taking main's ("theirs") side is correct (T-0479). But it treats
  design/frob.strata and docs/design/registry/capability-via-ratchet.
  lock.json exactly the same way -- neither is a ticket-ledger file
  (only tickets.md/tickets-archive.md get a real ledger splice via
  `_splice_and_stage`/`_splice_and_stage_archive`), so a conflict on
  either one fell straight into the blind `git checkout --theirs`
  branch and got silently resolved, discarding the worktree's
  independently-written via-list/accepted-count declaration with zero
  error surfaced anywhere -- exactly the measured T-4492 incident.

  This mirrors the T-1434 defect class (frob-coverage.lock.json getting
  blindly overwritten by the same mechanism), except a via-list/ratchet-
  count conflict has no safe elementwise merge the way two coverage
  percentages do -- there is no "higher of both sides" for two
  independently-declared capability grants, so the correct move is to
  refuse and name both sides, not merge them.

Fix:
  - Added `_CAPABILITY_RATCHET_PATHS` (design/frob.strata and the
    capability-via-ratchet lock) as a third excluded-from-blind-checkout
    class in `_auto_resolve_out_of_scope_conflicts`, alongside the
    existing tickets.md/tickets-archive.md exclusion and the T-1434
    coverage-lock special case. Any conflict on one of these two paths
    is left in `still_conflicted` instead of being checked out to
    "theirs" -- the caller (`_check_only_tickets_conflicted`) then
    aborts the merge and returns `Err(MergeConflict)` exactly as it
    already does for a genuine in-scope conflict.
  - Added `_land_ticket_for_commit_touching(cwd, ref, path)`: reads the
    most recent commit subject touching `path` at `ref` and extracts a
    `land T-xxxx` ticket id via regex (the exact subject shape
    `_commit_message`, frob.tickets._land_merge, always produces for a
    real squash-apply land). Used to name BOTH sides (worktree's HEAD
    and main's MERGE_HEAD) in the refusal's ERROR log -- best-effort
    only, never load-bearing for the refusal itself.
  - Neither file is merged (unlike the coverage lock's elementwise-max):
    a genuinely divergent via-list edit has no safe combination, so this
    always refuses rather than guesses.

Why _land.py was untouched:
  Scope included it in case the refusal message or main_branch threading
  needed a change there, but `_check_only_tickets_conflicted`'s existing
  abort-and-log-remaining-conflicts path already does everything needed
  once `_auto_resolve_out_of_scope_conflicts` correctly reports the
  capability-ratchet paths as still-conflicted -- no caller-side change
  was required.

Tests added (tests/unit/test_land_merge_conflict_drop.py, self-contained
per the tests/unit/test_land_sibling_regression.py precedent -- kept out
of the shared tests/ticket_land_suite/test_land_core.py to avoid a scope
collision with any ticket holding a lease on that file):
  - test_conflicting_strata_via_list_refuses_instead_of_dropping: worktree
    and main both add a DIFFERENT entry to design/frob.strata's via-list
    on the same line, worktree's ticket scoped to an unrelated file only
    (mirrors T-4492's actual shape -- design/frob.strata was NOT in that
    ticket's declared scope). Asserts `land()` returns
    `Err(LandError.MergeConflict)` and that main's file was never
    silently rewritten to drop the worktree's declaration.
  - test_conflicting_ratchet_lock_refuses_instead_of_dropping: same shape
    for docs/design/registry/capability-via-ratchet.lock.json's
    accepted_count field.

Regression check: re-ran the pre-existing tests this change could break
-- TestOutOfScopeConflictAutoResolved (an ORDINARY out-of-scope file
still auto-resolves to main's side, unaffected), TestCoverageLockConflict
Merges (T-1434's coverage-lock elementwise-max merge, unaffected, since
it is checked before the new capability-ratchet branch), Test
MergeConflictOutsideLedger (a genuine in-scope conflict still aborts),
and TestSiblingStateRegressionGuard (T-1914's own guard) -- all pass, 19/19.

Amendment (c) housekeeping: design/frob.strata and docs/design/registry/
capability-via-ratchet.lock.json were added to T-4498's scope (via
`frob ticket scope --add`) since the new test file execs git
subprocesses and reads/writes fixture files. Added
tests/unit/test_land_merge_conflict_drop.py to design/frob.strata's
`testsuite` node's exec, fs.read, and fs.write via-lists (one new site
in each), and bumped the matching three accepted_count entries in
capability-via-ratchet.lock.json by 1 each with a T-4498 reason/ticket.

Verification performed (ruff + serial pytest only, per instruction --
no ticket-scoped `frob check`, no `frob ticket done-report`):
  ruff check src/frob/tickets/_land_git_ops.py
             tests/unit/test_land_merge_conflict_drop.py
    -> All checks passed!
  ruff format --check (same files) -> already formatted (after one
    `ruff format` pass that reflowed the new docstrings/log calls).
  PYTHONPATH=<WT>/src <venv>/bin/python -m pytest -q -p no:cacheprovider
    -p no:xdist tests/unit/test_land_merge_conflict_drop.py
    tests/unit/test_land_sibling_regression.py
    "tests/ticket_land_suite/test_land_core.py::TestOutOfScopeConflictAutoResolved"
    "tests/ticket_land_suite/test_land_core.py::TestCoverageLockConflictMerges"
    "tests/ticket_land_suite/test_land_core.py::TestMergeConflictOutsideLedger"
    -> 19 passed, 0 failed.

Files changed (all under this worktree):
  /home/logan/projects/frob/.claude/worktrees/t-4498/src/frob/tickets/_land_git_ops.py
  /home/logan/projects/frob/.claude/worktrees/t-4498/tests/unit/test_land_merge_conflict_drop.py
  /home/logan/projects/frob/.claude/worktrees/t-4498/design/frob.strata
  /home/logan/projects/frob/.claude/worktrees/t-4498/docs/design/registry/capability-via-ratchet.lock.json

Not done (explicitly, per amendment b): ticket-scoped `frob check`,
`frob ticket evidence`/`--designate-repro`, and `frob ticket
done-report` were NOT run -- the coordinator owns those steps for this
ticket. This narrative substitutes for the Done report.

Nothing found outside scope during this work; no new tickets filed.

### Changed
```
 CHANGELOG.md                                       |   3 +
 design/frob.strata                                 |  12 +-
 .../registry/capability-via-ratchet.lock.json      |  18 +-
 src/frob/tickets/_land_git_ops.py                  | 146 ++++++++++++----
 tests/unit/test_land_merge_conflict_drop.py        | 186 +++++++++++++++++++++
 tickets/T-4498/done-report.md                      | 143 ++++++++++++++++
 tickets/T-4498/ticket.md                           |   5 +-
 7 files changed, 464 insertions(+), 49 deletions(-)
```

### Evidence
- `tests/unit/test_land_merge_conflict_drop.py::TestCapabilityRatchetConflictRefused::test_conflicting_strata_via_list_refuses_instead_of_dropping` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 24 error(s), 5008 warning(s), 980 waived
- error-findings: ARCH103@src/frob/app/config.py, ARCH103@src/frob/doctor.py, CROSSTICKET001@docs/commands/check.md, CROSSTICKET001@docs/modules/app.md, CROSSTICKET001@docs/modules/tickets-landing.md, CROSSTICKET001@src/frob/__main__.py, CROSSTICKET001@src/frob/_cli_parsers/_check.py, CROSSTICKET001@src/frob/_cli_parsers/_ticket/_progress.py, CROSSTICKET001@src/frob/app/_config_external.py, CROSSTICKET001@src/frob/app/check_runner.py, CROSSTICKET001@src/frob/app/config.py, CROSSTICKET001@src/frob/app/ticket_runner/_land_cmd.py, CROSSTICKET001@src/frob/app/ticket_runner/_verify.py, CROSSTICKET001@src/frob/dup/_legacy_cs.py, CROSSTICKET001@src/frob/gates/__init__.py, DOC005@docs/modules/cli.md, DUP001@tests/unit/test_land_merge_conflict_drop.py, MILE001@tickets.md, PERF004@src/frob/doctor.py, REF002@src/frob/vet/_capability_registry/_dotnet_bcl.py, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4512.json, TICK010@/home/logan/projects/frob/.git/frob-leases/T-4550.json, WIRE002@src/frob/dup/_legacy_cs.py, invalid-argument-type@tests/unit/test_ticket_runner_land_cmd_flags.py
