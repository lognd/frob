---
id: T-2170
title: 'reclaim_orphaned_squash_residue has ZERO production callers: T-2157 shipped
  the primitive but wiring it into land() startup needs _land.py, so orphaned staged
  residue still blocks the fleet'
state: done
kind: bug
origin: human
created: '2026-08-11'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_land_git_ops.py
- docs/design/land-checkpoint-durability.md
evidence_scope:
- tests/unit/test_land_squash_residue_reclaim.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_git_ops.py
  reason: COV001/TEST001/ARCH103 residue for reclaim_orphaned_squash_residue attributed
    to T-2170; also need to import it into _land.py which requires editing its docstring
    reference
  actor: logan
  at: '2026-08-11'
- op: add
  glob: docs/design/land-checkpoint-durability.md
  reason: add frob:doc anchor for reclaim_orphaned_squash_residue now wired into land()
  actor: logan
  at: '2026-08-11'
evidence:
- tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup::test_orphaned_residue_from_a_dead_land_is_cleared_before_the_dirtymain_refusal
- tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup::test_land_calls_reclaim_before_acquiring_its_own_lock
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_does_not_touch_a_live_lands_own_staging
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_clean_root_is_a_no_op
designated_repro_test: tests/unit/test_land_squash_residue_reclaim.py::TestLandCallsReclaimAtStartup::test_orphaned_residue_from_a_dead_land_is_cleared_before_the_dirtymain_refusal
threat: null
component: null
anchor: false
anchor_reason: null
---
