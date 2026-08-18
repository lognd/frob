---
id: T-2462
title: defer pyproject.toml/.frob-release.json version bump to an explicit release-cut,
  matching T-2445's CHANGELOG.md fragment deferral
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/__init__.py
- src/frob/app/ticket_runner/_close_cmd.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/release/_fragments.py
- tests/unit/test_ticket_runner_land_release.py
- tests/test_ticket_land.py
- docs/modules/tickets-landing.md
- tests/unit/test_close_rel001_bump.py
- tests/unit/gates/test_rel001_deferred_bump.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_ticket_runner_land_release.py
  reason: T-2462 changes _write_release_bump/_apply_release_bump_for_land's tested
    contract (pyproject.toml/.frob-release.json no longer bumped per-land); these
    two files directly assert the old per-land bump behavior and must be updated to
    match
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_ticket_land.py
  reason: T-2462 changes _write_release_bump/_apply_release_bump_for_land's tested
    contract (pyproject.toml/.frob-release.json no longer bumped per-land); these
    two files directly assert the old per-land bump behavior and must be updated to
    match
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'step 9.6''s own documented REL001 land-time behavior changes: pyproject.toml/.frob-release.json
    are no longer rewritten per land'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_close_rel001_bump.py
  reason: T-2462 adds _rel001_fragment_exists_for_ticket (_close_cmd.py, existing
    test file) and _rel001_fragments_pending/_rel001_deferred_note (gates/__init__.py,
    new file -- tests/test_gates.py is leased by concurrent T-2454)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/gates/test_rel001_deferred_bump.py
  reason: T-2462 adds _rel001_fragment_exists_for_ticket (_close_cmd.py, existing
    test file) and _rel001_fragments_pending/_rel001_deferred_note (gates/__init__.py,
    new file -- tests/test_gates.py is leased by concurrent T-2454)
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one
- tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry
- tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
- tests/unit/gates/test_rel001_deferred_bump.py::TestReleaseGatePlainCheckoutDeferredPosture::test_pending_bump_with_fragment_is_warn_not_error
- tests/unit/gates/test_rel001_deferred_bump.py::TestReleaseGatePlainCheckoutDeferredPosture::test_pending_bump_without_fragment_stays_error
- tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyFragmentSatisfies::test_fragment_present_satisfies_even_though_pyproject_undeclared
- tests/unit/test_close_rel001_bump.py::TestOwnObligationsRelBumpDirtyFragmentSatisfies::test_no_fragment_and_no_bump_still_dirty
designated_repro_test: null
evidence_changes:
- old_node: tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_writes_fragment_and_regenerates_changelog_no_pyproject_touch
  new_node: tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump::test_rewrites_version_and_prepends_changelog_entry
  reason: renamed back to the pre-existing evidence-bound name shared by T-0338/T-1089
    to avoid orphaning their evidence (OrphanedEvidenceDeletion land guard); content
    updated in place to match the new deferred-bump contract
  actor: logan
  at: '2026-08-18'
- old_node: tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_needed_writes_fragment_but_returns_none_and_never_stamps
  new_node: tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand::test_bump_applies_writes_and_stamps
  reason: renamed back to the pre-existing evidence-bound name shared by T-1007/T-1009/T-1089/T-1593/T-0338
    to avoid orphaning their evidence (OrphanedEvidenceDeletion land guard); content
    updated in place to match the new deferred-bump contract
  actor: logan
  at: '2026-08-18'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 2bd1f74d9ca73dfa80b86ed8b56d4d27e8b3bb3b
---
T-2445 landed changelog.d/T-####.md fragments so CHANGELOG.md's write is collision-free and self-healing under land interruption, but left pyproject.toml's version line and .frob-release.json's stamped manifest bumping on EVERY land, unchanged -- the other half of the measured 6-of-7-lands-touch-both-shared-files contention T-2445 was filed to close.

A fuller design defers that bump too, to an explicit release-cut (frob release assemble, or folded into frob release publish) reading the same changelog.d/ fragments' bump: header to compute the accumulated max bump class. This needs, in the same leaf (both ripple together, do not split):
- frob.gates.release_gate (REL001): the plain-root-checkout ERROR path (_rel001_version / _changelog_mentions) must learn a 'deferred via fragments, not silently missing' WARN posture, mirroring _rel001_land_owned's existing informational-not-error precedent, or every frob check on main will start erroring forever the moment nothing bumps pyproject.toml per land.
- frob.app.ticket_runner._close_cmd._own_obligations_rel_bump_dirty: the close-time REL001 preflight currently treats 'pyproject.toml already covers the diff' as the not-dirty signal; it needs to also accept 'a changelog.d/T-####.md fragment already exists for this ticket' as satisfying the obligation, or every ticket whose scope touches public API becomes permanently un-closeable between release cuts.

Not started: this ticket's own src/frob/gates/__init__.py scope was leased by a concurrent ticket (T-2435) at T-2445's dispatch time, so T-2445 deliberately scoped this half out rather than attempt it without the file. Re-check the lease before starting.