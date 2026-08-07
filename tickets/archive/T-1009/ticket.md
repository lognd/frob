---
id: T-1009
title: 'single-source version: frob release sync regenerates the quartet + REL coherence
  error'
state: done
kind: feature
origin: human
created: '2026-07-27'
priority: high
parent: T-1008
tier: ticket
sprint: null
scope:
- src/frob/**
- Makefile
- tests/**
- docs/modules/release.md
- docs/modules/app.md
- docs/modules/tickets.md
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/release.md
  reason: 'AFFECT001 requires the frob:doc-anchored docs to be touched in the same
    diff as the functions they document; frob release sync (release_runner.py/release/__init__.py)
    and the T-1007 land-callback fix (ticket_runner.py) both carry frob:doc anchors
    into docs/modules/release.md, docs/modules/app.md, and docs/modules/tickets.md.
    Adding those doc files to scope so the gate can be satisfied in this same change
    rather than deferred.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/app.md
  reason: 'AFFECT001 requires the frob:doc-anchored docs to be touched in the same
    diff as the functions they document; frob release sync (release_runner.py/release/__init__.py)
    and the T-1007 land-callback fix (ticket_runner.py) both carry frob:doc anchors
    into docs/modules/release.md, docs/modules/app.md, and docs/modules/tickets.md.
    Adding those doc files to scope so the gate can be satisfied in this same change
    rather than deferred.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/tickets.md
  reason: 'AFFECT001 requires the frob:doc-anchored docs to be touched in the same
    diff as the functions they document; frob release sync (release_runner.py/release/__init__.py)
    and the T-1007 land-callback fix (ticket_runner.py) both carry frob:doc anchors
    into docs/modules/release.md, docs/modules/app.md, and docs/modules/tickets.md.
    Adding those doc files to scope so the gate can be satisfied in this same change
    rather than deferred.

    '
  actor: logan
  at: '2026-07-27'
- op: add
  glob: docs/modules/gates.md
  reason: 'AFFECT001 requires the frob:doc-anchored docs to be touched in the same
    diff as the functions they document; frob release sync (release_runner.py/release/__init__.py)
    and the T-1007 land-callback fix (ticket_runner.py) both carry frob:doc anchors
    into docs/modules/release.md, docs/modules/app.md, and docs/modules/tickets.md.
    Adding those doc files to scope so the gate can be satisfied in this same change
    rather than deferred.

    '
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_release.py::TestAuthoritativeVersion::test_reads_manifest_version
- tests/test_release.py::TestAuthoritativeVersion::test_no_manifest_is_err
- tests/test_release.py::TestRewritePyprojectVersion::test_rewrites_when_different
- tests/test_release.py::TestRewritePyprojectVersion::test_noop_when_already_matches
- tests/test_release.py::TestRewritePyprojectVersion::test_no_version_line_is_err
- tests/test_release.py::TestRewritePyprojectVersion::test_missing_file_is_err
- tests/test_release.py::TestChangelogSkeletonEntry::test_inserts_new_entry
- tests/test_release.py::TestChangelogSkeletonEntry::test_existing_entry_is_noop
- tests/test_release.py::TestChangelogSkeletonEntry::test_missing_changelog_is_noop
- tests/test_release.py::TestReleaseGateCoherence::test_clean_repo_has_no_rel002
- tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_pyproject_fires_rel002
- tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_uv_lock_fires_rel002
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_no_manifest_is_noop
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_class_none_is_noop
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_unreadable_graph_fails
- tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_reads_head_manifest_not_worktree_disk_copy
- tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead::test_no_manifest_at_head_returns_none
- tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_no_manifest_exits_1
- tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_regenerates_all_artifacts
- tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_already_in_agreement_is_quiet_but_still_locks
- tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_uv_lock_failure_exits_1
- tests/unit/test_app_runners_batch5.py::TestReleaseSyncRunner::test_sync_bad_pyproject_version_line_exits_1
- tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one
designated_repro_test: null
acceptance:
- text: given any one artifact hand-edited out of agreement, when frob check runs,
    then a REL error names the disagreeing files; given frob release sync, all four
    agree afterward
  evidence:
  - tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_pyproject_fires_rel002
- text: 'T-0756 fixture proof: given pyproject.toml hand-edited out of agreement with
    .frob-release.json''s authoritative version, when release_gate (the production
    REL002 invocation frob check --only release runs) is called against that tree,
    then it FAILS with an ERROR-severity REL002 finding naming pyproject.toml; given
    the same tree with pyproject.toml matching the manifest (the clean/synced state),
    then the same production call PASSES with no REL002 finding'
  evidence:
  - tests/test_release.py::TestReleaseGateCoherence::test_hand_edited_pyproject_fires_rel002
  - tests/test_release.py::TestReleaseGateCoherence::test_clean_repo_has_no_rel002
threat: null
component: null
---
Child 1 of T-1008. The version lives ONCE in .frob-release.json; frob release sync regenerates pyproject.toml version, uv.lock (via uv lock), and the CHANGELOG skeleton entry from it; a REL coherence check errors when any of the four disagree (catching hand-edits immediately instead of at the next land). Fold T-1007 (bump-callback baseline from root) into this: with a single source + sync, the callback reads the manifest on ROOT and the whole stale-worktree class dies. Update the land path and make upload to use sync.