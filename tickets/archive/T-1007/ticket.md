---
id: T-1007
title: land REL001 bump callback derives baseline from worktree-carried manifest (guard
  fires each time; fix the producer)
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: high
parent: T-0999
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner.py
- tests/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_no_manifest_is_noop
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_class_none_is_noop
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails
- tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_reads_head_manifest_not_worktree_disk_copy
- tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_no_manifest_at_head_returns_none
designated_repro_test: null
acceptance:
- text: given a worktree carrying a stale version, when its ticket lands, then the
    bump computes main+1 on the first attempt with no guard refusal
  evidence:
  - tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_reads_head_manifest_not_worktree_disk_copy
threat: null
component: null
---
T-0992 added the land-side monotonicity backstop and it has now correctly REFUSED a third stale-bump attempt (T-0997 land computed 0.183.0 vs main 0.184.0). But the producer bug remains: _apply_release_bump_for_land derives its baseline from the worktree-carried release manifest/pyproject that rode the squash. Fix the callback to read the baseline from ROOT current state (same git-show technique as the guard) so the guard becomes a never-fires invariant instead of a per-land speed bump requiring a manual worktree merge. Churn-epic member: each guard refusal costs a merge+reland round trip.