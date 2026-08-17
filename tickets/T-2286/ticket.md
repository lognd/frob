---
id: T-2286
title: reclaim_orphaned_squash_residue silently discards genuine dirty-main content
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land_git_ops.py
- src/frob/tickets/_land.py
- docs/design/land-checkpoint-durability.md
- tests/unit/test_land_squash_residue_reclaim.py
evidence_scope:
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/land-checkpoint-durability.md
  reason: 'T-2286: cross-reference the marker-based fix in its existing design doc,
    and update the reclaim-family fixture/regression test the fix directly touches'
  actor: logan
  at: '2026-08-17'
- op: add
  glob: tests/unit/test_land_squash_residue_reclaim.py
  reason: 'T-2286: cross-reference the marker-based fix in its existing design doc,
    and update the reclaim-family fixture/regression test the fix directly touches'
  actor: logan
  at: '2026-08-17'
evidence:
- tests/test_ticket_land.py::TestLand::test_refuses_on_dirty_main
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
- tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_dirty_without_a_marker_is_never_reclaimed
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging
designated_repro_test: tests/test_ticket_land.py::TestLand::test_refuses_on_dirty_main
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-2283 (2026-08-17): three of T-2283's four target
tests fail because of a genuine defect, not a stale test:

    tests/test_ticket_land.py::TestLand::test_refuses_on_dirty_main
    tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_with_other_change_still_refuses
    tests/test_ticket_land.py::TestUvLockSync::test_dirty_lock_version_plus_other_line_still_refuses

Root cause: T-2170 wired reclaim_orphaned_squash_residue
(src/frob/tickets/_land_git_ops.py) into land()
(src/frob/tickets/_land.py) to run BEFORE _refuse_if_main_dirty's own
DirtyMain check, specifically to auto-heal a DEAD land's staged
squash-merge residue so it does not permanently block the fleet.

The trouble is reclaim_orphaned_squash_residue's actual test for "is
this orphaned residue" is just "root has ANY uncommitted change AND
land.lock is currently free" (_porcelain_dirty plus a non-blocking
flock probe) -- it never checks that the dirt actually resembles
squash-merge staging at all. So ANY dirty main -- a stray uncommitted
file, a real hand-edited uv.lock, anything -- gets silently
git-reset-hard plus git-clean-fd'd away the moment land.lock happens
to be free (the common case), before _refuse_if_main_dirty ever gets
a chance to see the dirt and refuse. The DirtyMain safety check is
effectively defeated for every land where nothing else currently
holds land.lock, and genuine uncommitted content on main is silently
destroyed rather than reported.

Confirmed directly: test_refuses_on_dirty_main writes a dirty.txt
file to repo, then calls land(..., dry_run=True) expecting
Err(LandError.DirtyMain); instead land succeeds (Ok) and dirty.txt is
gone -- silently discarded by the reclaim call before the dirty check
runs. Same shape for both TestUvLockSync cases with a genuinely-dirty
uv.lock.

This needs a real fix distinguishing "orphaned squash-merge residue
from a DEAD land" from "arbitrary unrelated dirt on main" -- e.g. some
positive signal (a stamp/marker land() itself writes before staging,
that the reclaim path can verify a match against) rather than the
current "any dirt + free lock => assume orphaned" heuristic. Out of
T-2283's own declared scope (tests/test_ticket_land.py,
src/frob/tickets/_land.py only) since the actual reclaim logic and its
classification live in src/frob/tickets/_land_git_ops.py, and a correct
fix needs design thought this ticket did not force through.