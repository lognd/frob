## Done report

Diagnosed all four pre-existing failures individually, per-test:

1. TestLand::test_refuses_on_dirty_main -- CODE WRONG, real defect.
2. TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice -- TEST WRONG, fixed.
3. TestUvLockSync::test_dirty_lock_with_other_change_still_refuses -- CODE WRONG, same root cause as (1).
4. TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses -- CODE WRONG, same root cause as (1).

Root cause of (1)/(3)/(4): T-2170 wired reclaim_orphaned_squash_residue
(src/frob/tickets/_land_git_ops.py) into land() to run BEFORE
_refuse_if_main_dirty's DirtyMain check. That function's actual test
for "orphaned residue" is just "root has ANY uncommitted change AND
land.lock is free" -- it never verifies the dirt resembles squash-merge
staging. Result: any dirty main (a stray file, a real uv.lock edit,
anything) gets silently git-reset-hard + git-clean-fd'd before
DirtyMain ever sees it, whenever nothing else holds land.lock (the
common case). This defeats the DirtyMain safety check and silently
destroys genuine uncommitted content on main. Confirmed directly by
observing dirty.txt vanish and land() return Ok instead of
Err(DirtyMain).

This is out of T-2283's declared scope (tests/test_ticket_land.py,
src/frob/tickets/_land.py) since the classification logic lives in
src/frob/tickets/_land_git_ops.py and a correct fix needs a real
positive signal distinguishing dead-land residue from arbitrary dirt
-- design work this ticket did not force through. Filed as its own
bug ticket: T-2286 (reclaim_orphaned_squash_residue
silently discards genuine dirty-main content), scope
src/frob/tickets/_land_git_ops.py + src/frob/tickets/_land.py,
priority high given the silent-data-loss shape.

Root cause of (2): T-2079 (landed today) added
enforce_ticket_ownership, which correctly refuses a write_ticket()
call from main against a ticket currently leased to a worktree --
exactly the write pattern this test used to seed its "main
independently retitles" step. The test's own intent (drive land()'s
MergeConflict path with a genuine same-line textual conflict) has
nothing to do with the ownership guard, so it now writes the
conflicting edit as a raw file write instead of through write_ticket
-- the same shape an out-of-band edit (direct commit, cherry-pick,
different tool) would actually take reaching main outside frob's own
API. Verified FAILED_AT_PARENT via --check-repro before designating.

Full tests/test_ticket_land.py run (280 collected) after the fix:
277 pass, only the 3 code-wrong cases above still fail -- no
previously-passing test broken by the test-wrong fix.

Changed:
- tests/test_ticket_land.py::TestLedgerV2LandMergeStory.test_same_ticket_conflict_surfaces_loudly_no_splice

Evidence: tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice (--accepts 0, designated repro, FAILED_AT_PARENT confirmed)

Filed: T-2286 (bug: reclaim_orphaned_squash_residue silently discards genuine dirty-main content -- covers tests 1/3/4)

Gates: not run to full green -- T-2283's own acceptance ("All 4 named
tests pass") cannot be met within its declared scope, since 3 of the
4 require a fix in src/frob/tickets/_land_git_ops.py. Blocking T-2283
on the newly filed bug ticket rather than forcing a workaround or
closing against an unmet acceptance criterion.

### Changed
```
 tests/test_ticket_land.py          | 21 +++++++++---
 tickets/T-2283/ticket.md           |  9 ++++--
 tickets/T-2286/ticket.md | 66 ++++++++++++++++++++++++++++++++++++++
 3 files changed, 88 insertions(+), 8 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLedgerV2LandMergeStory::test_same_ticket_conflict_surfaces_loudly_no_splice` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2283/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2283/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2283/src/frob/lang/_nodes.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2283/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2283/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2283, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
