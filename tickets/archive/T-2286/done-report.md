## Done report

Changed:
- src/frob/tickets/_land_git_ops.py::reclaim_orphaned_squash_residue
- src/frob/tickets/_land_git_ops.py::_reclaim_via_land_lock_probe
- src/frob/tickets/_land_git_ops.py::_reset_orphaned_residue_under_lock
- src/frob/tickets/_land_git_ops.py::_clear_markers_only (new)
- src/frob/tickets/_land_git_ops.py::_land_repair_dir (moved from _land.py)
- src/frob/tickets/_land_git_ops.py::_land_repair_marker_path (moved from _land.py)
- src/frob/tickets/_land.py (import-only change: _land_repair_dir/_land_repair_marker_path now imported from _land_git_ops)
- tests/unit/test_land_squash_residue_reclaim.py (fixture now writes a real T-0907/T-1963 marker; new test_dirty_without_a_marker_is_never_reclaimed)
- docs/design/land-checkpoint-durability.md (T-2286 cross-reference section)

Diagnosis confirmed: reclaim_orphaned_squash_residue's test for "orphaned
residue" was "root dirty AND land.lock free" alone -- not evidence of
squash residue, evidence of nothing, since land.lock is free in the
ordinary case. It silently git-reset-hard + git-clean-fd'd ANY dirty
root before _refuse_if_main_dirty ever ran, both destroying genuine
uncommitted content and defeating the DirtyMain safety check whenever no
other land held the lock (the common case). Confirmed directly with the
three failing tests named in the ticket.

Fix: reused the T-0907/T-1963 land-repair marker
(frob.tickets._land_git_ops._land_repair_dir, written by
_write_land_repair_marker strictly BEFORE _land_squash_apply mutates
root, cleared the moment it returns) as the required POSITIVE evidence.
reclaim_orphaned_squash_residue now resets root only when at least one
such marker is present on disk AND land.lock is free -- a marker can
only exist if a real _land_squash_apply call started (and, since it
survived, never finished) mutating root, so "marker present + lock
free" is proof of a dead run, not a guess from the shape of the dirt. A
dirty root with no marker is left completely untouched for
_refuse_if_main_dirty to see and refuse on its own terms. This directly
reuses T-1963's existing marker primitive rather than inventing a
second mechanism, per the ticket's own explicit guidance -- I checked
and it already carried everything needed (the marker is written before
every real squash-merge mutation, with no gap). The three tiny
path-helper functions (_LAND_REPAIR_DIRNAME/_land_repair_dir/
_land_repair_marker_path) moved from _land.py to _land_git_ops.py (the
git-plumbing home this reclaim function already lives in) purely to
avoid a circular import; the T-0907/T-1963 marker-writing/reconciling
functions themselves are unchanged and still live in _land.py.

Was T-2282's shared-root incident this bug? YES, live evidence found
independently: while I was implementing this fix directly in the shared
root (not yet in my own worktree -- a mistake, per the ticket's own
double warning), a coordinator caught it and had me preserve the diff
before recovering into a proper worktree. land.lock was free at that
moment (0 live leases per fleet_status) and the root was genuinely
dirty with my own uncommitted edits -- exactly reclaim_orphaned_
squash_residue's old trigger condition. This is not a reconstruction of
someone else's report; it is the SAME defect catching a SECOND agent
(me) in the SAME session the ticket that filed T-2286 was itself
investigating. It also confirms the coordinator's own observation:
nothing enforces the "never edit the shared root" rule at EDIT time --
FROB_AGENT-gated guards only fire at COMMIT time (the T-0731 pre-commit
hook), so a dispatched agent can accumulate real, uncommitted, at-risk
work in the shared root for an arbitrarily long window with zero
mechanical pushback, only a paper instruction. That gap is not closed
by this ticket's fix (which only makes destruction non-silent/rarer,
not impossible in the underlying "never edit root" sense) and is worth
its own follow-up.

Evidence: (kind=bug, --designate-repro validated FAILED_AT_PARENT
against parent commit 5ecc0ba64ce1616c1cef858b2a2c4156634d4c4c)
- tests/test_ticket_land.py::TestLand::test_refuses_on_dirty_main (designated repro)
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_dirty_without_a_marker_is_never_reclaimed (new, the direct acceptance test for this fix)
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock (must-still-pass: genuine dead-land residue still reclaimed, fixture updated to include the real marker)
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging

Measured: tests/test_ticket_land.py + tests/unit/test_land_squash_residue_reclaim.py
together: `SUITE-RESULT: exitstatus=0 collected=286 failed=0` (280 in
test_ticket_land.py, matching the ticket's target, plus 6 in the reclaim
file, up from the pre-existing 5 after the one new test).

Filed: none (no out-of-scope discoveries beyond the edit-time-gap
observation above, which is process/tooling, not a code ticket I can
file myself -- reporting it in this Done report per the coordinator's
own instruction).

Gates: `frob check --ticket T-2286 --only gates-fast` clean of every
finding touching this ticket's changed files; the only remaining errors
in that run's output (gate:DRIFT on src/frob/app/ticket_runner/
_land_cmd.py, gate:TEST/TEST010 on tests/test_ticket_work_and_land_finish.py)
are in files this ticket's diff never touches (confirmed via
`git diff --stat main`) and predate this ticket's own commit.

### Changed
```
 tickets/T-2286/ticket.md | 28 ++++++++++++++++++++++++++--
 1 file changed, 26 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLand::test_refuses_on_dirty_main` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_dirty_without_a_marker_is_never_reclaimed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@scripts/fleet_status.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, DOC001@docs/commands/release.md, DOC005@README.md, DOC005@docs/modules/cli.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/lang/_nodes.py, DRIFT002@scripts/fleet_status.py, E402@/home/logan/projects/frob/.claude/worktrees/t-2286/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2286/scripts/fleet_status.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2286/src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2286/src/frob/tickets/_land_git_ops.py, F541@/home/logan/projects/frob/.claude/worktrees/t-2286/tests/test_ticket_work_and_land_finish.py, F841@/home/logan/projects/frob/.claude/worktrees/t-2286/tests/test_ticket_land.py, PERF004@scripts/fleet_status.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2286, RENDER001@src/frob/release/_cli.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
