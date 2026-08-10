---
id: T-2046
title: T-2026's auto-heal requires a SOLE dirty path, so it declines whenever two
  interrupted ticket dirs coexist -- the normal high-load state it was built for
state: done
kind: bug
origin: human
created: '2026-08-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land.py
  reason: narrow to the auto-heal guard and its unit test
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/tickets/test_land.py
  reason: narrow to the auto-heal guard and its unit test
  actor: logan
  at: '2026-08-10'
- op: remove
  glob: tests/unit/tickets/test_land.py
  reason: correct scope to the actual existing test file for this guard
  actor: logan
  at: '2026-08-10'
- op: add
  glob: tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py
  reason: correct scope to the actual existing test file for this guard
  actor: logan
  at: '2026-08-10'
evidence:
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
- tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing
designated_repro_test: tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
acceptance:
- text: A test with TWO untracked, cleanly-parsing tickets/T-####/ directories asserts
    the guard fires and both are committed; this test must fail before the fix.
  evidence:
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
- text: A test that a mixed dirty tree (one valid untracked ticket dir plus one modified
    tracked file) causes the guard to decline entirely and commit nothing.
  evidence:
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing
- text: A test that N directories where one fails to parse results in no commits at
    all.
  evidence:
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing
- text: Report whether the two precedent guards in _land_git_ops.py have the same
    class-vs-instance mismatch, or whether SOLE is genuinely correct for them.
  evidence:
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_two_well_formed_orphaned_dirs_are_both_committed
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_mixed_valid_dir_plus_modified_tracked_file_commits_nothing
  - tests/unit/test_land_dirty_main_orphaned_ticket_t2026.py::TestCommitOrphanedNewTicketDirOnlyDriftMultiple::test_one_unparseable_dir_among_several_commits_nothing
threat: null
component: null
anchor: false
anchor_reason: null
---
## Problem

T-2026's auto-heal (`_commit_orphaned_new_ticket_dir_only_drift`,
`src/frob/tickets/_land.py:1919`) fires ONLY when a single untracked
`tickets/T-####/` directory is the **SOLE** dirty path. At the agent count
that produces the residue in the first place, there is routinely more than
one -- so the guard declines in precisely the scenario it was built for, and
the `DirtyMain` deadlock it exists to prevent happens anyway.

## Measured evidence (2026-08-10, ~30 minutes after T-2026 landed)

T-2026 landed at `82bf70c5c` and is `state: done`. Immediately afterwards,
with 7-8 agents dispatched:

    $ python3 scripts/fleet_status.py
    ROOT DIRTY -- do not dispatch
      ?? tickets/T-2042/
      ?? tickets/T-2045/

Both directories contained exactly one file, `ticket.md`, both parsing
cleanly -- i.e. each one INDIVIDUALLY satisfies every safety condition the
guard checks. The guard declined solely because there were TWO of them.
The coordinator had to clear the deadlock by hand (`git add` + `git commit`),
which is the exact manual intervention T-2026 was filed to eliminate.

This is not a rare race. `frob ticket new` refuses under `LandInProgress`
almost continuously at high agent counts (T-2026's own body says so), so
multiple interrupted `new` invocations coexisting is the NORMAL high-load
state, not an unlucky one.

## Root cause

The SOLE-dirty-path restriction was inherited from the two precedent guards
in `_land_git_ops.py` (`_restore_lock_version_only_drift`,
`_commit_rapid_debt_only_drift`). For those it is correct: each guards ONE
specific known file, so "this file and nothing else" is the right shape.

It does not transfer. This guard matches a CLASS of paths (any untracked,
cleanly-parsing new ticket directory), and the safety argument -- a freshly
created untracked directory has no prior state to clobber, so committing it
once it parses is always safe -- holds identically for N such directories as
for one. The restriction buys no safety here; it only shrinks the guard's
reach below the load it was designed for.

Note the coordinator explicitly approved the sole-path shape when the design
was proposed. This ticket corrects that decision, not the implementer's work.

## Proposed fix

Fire when **EVERY** dirty path is an untracked `tickets/T-####/` directory
whose only entry is `ticket.md` and which parses cleanly with the parsed id
matching the directory name. If ANY dirty path fails those conditions, the
guard must still decline entirely and let the ordinary `DirtyMain` refusal
fire -- do not partially heal a mixed dirty tree.

Keep every existing safety property: parse-before-commit, no touching of
modified TRACKED files, no directory containing anything besides
`ticket.md`, and the LOUD commit message plus log line naming it as an
auto-heal of another process's residue.

## Do NOT fix it this way

- Do NOT drop the parse check to simplify the multi-path loop. Parsing is
  what separates "safe to commit" from "committing a torn write", and it
  must hold for EVERY directory, not just the first.
- Do NOT partially heal -- committing the two valid dirs while a third
  unmatched dirty path remains would leave the tree dirty anyway AND
  publish content under a guard that had already declined. All-or-nothing.
- Do NOT extend this to modified TRACKED `ticket.md` files. T-2026 cut that
  case deliberately: an interrupted write to an existing file cannot be told
  apart from a genuine mid-write tear without per-verb transition
  validation. That cut still stands and is NOT in scope here.
- Do NOT "fix" this by making `frob ticket new` commit before writing, or by
  removing the write-then-commit window. That is a much larger change to a
  verb every agent depends on, and the guard is needed regardless for any
  process killed at an unlucky moment.

## Acceptance criteria

1. A test with TWO untracked, cleanly-parsing `tickets/T-####/` directories
   asserting the guard fires and both are committed. THIS TEST MUST FAIL
   BEFORE THE FIX -- watch it fail and record the observed output.
2. A test that a mixed dirty tree (one valid untracked ticket dir plus one
   modified tracked file) causes the guard to decline entirely and commit
   NOTHING.
3. A test that N directories where one fails to parse results in NO commits
   at all.
4. Report whether the two precedent guards in `_land_git_ops.py` have the
   same class-vs-instance mismatch, or whether SOLE is genuinely correct for
   them. State the denominator; "checked both, SOLE is correct for each
   because they guard one named file" is a fine answer.