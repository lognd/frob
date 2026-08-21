---
id: T-2445
title: every land writes CHANGELOG.md and the version line, so scope-disjoint lands
  still conflict
state: done
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/release/_fragments.py
- src/frob/release/__init__.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/scaffold/project.py
- docs/modules/release.md
- docs/modules/tickets-landing.md
- tests/test_release.py
- tests/test_ticket_land.py
- tests/unit/test_land_cmd_backpressure.py
- tests/test_scaffold_worktree_lease_hook.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/release/_fragments.py
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/release/__init__.py
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/scaffold/project.py
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/release.md
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/tickets-landing.md
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_release.py
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_ticket_land.py
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/unit/test_land_cmd_backpressure.py
  reason: 'T-2445: fragment-per-ticket CHANGELOG.md (changelog.d/T-####.md), assembled
    deterministically every land under the existing land.lock -- kills the ad-hoc
    text-splice merge/interruption hazard; pyproject.toml/.frob-release.json bump-per-land
    left unchanged in this stage (REL001 gate change needs gates/__init__.py, leased
    by T-2435 -- filed as a follow-up)'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: tests/test_scaffold_worktree_lease_hook.py
  reason: 'T-2445: new guard-regression test for changelog.d/ land-owned refusal'
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_release.py::TestChangelogFragments::test_write_then_read_round_trips
- tests/test_release.py::TestChangelogFragments::test_read_sorts_numerically_not_lexically
- tests/test_release.py::TestChangelogFragments::test_read_fails_closed_on_a_malformed_fragment
- tests/test_release.py::TestChangelogFragments::test_assemble_writes_every_fragment_as_a_bullet
- tests/test_release.py::TestChangelogFragments::test_assemble_is_idempotent_and_picks_up_new_fragments
- tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one
- tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog_fragment
designated_repro_test: null
acceptance:
- text: Given two lands whose declared code scopes are disjoint, when both run, then
    neither requires a manual CHANGELOG or version conflict-resolution step.
  evidence:
  - tests/test_release.py::TestChangelogFragments::test_write_then_read_round_trips
  - tests/test_release.py::TestChangelogFragments::test_read_sorts_numerically_not_lexically
  - tests/test_release.py::TestChangelogFragments::test_read_fails_closed_on_a_malformed_fragment
  - tests/test_release.py::TestChangelogFragments::test_assemble_writes_every_fragment_as_a_bullet
  - tests/test_release.py::TestChangelogFragments::test_assemble_is_idempotent_and_picks_up_new_fragments
  - tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one
  - tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog_fragment
- text: Given a release cut after several concurrent lands, when the CHANGELOG is
    produced, then it contains every landed ticket's entry in correct order and the
    version bumped exactly once, proving conflicts were not resolved by dropping entries.
  evidence:
  - tests/test_release.py::TestChangelogFragments::test_write_then_read_round_trips
  - tests/test_release.py::TestChangelogFragments::test_read_sorts_numerically_not_lexically
  - tests/test_release.py::TestChangelogFragments::test_read_fails_closed_on_a_malformed_fragment
  - tests/test_release.py::TestChangelogFragments::test_assemble_writes_every_fragment_as_a_bullet
  - tests/test_release.py::TestChangelogFragments::test_assemble_is_idempotent_and_picks_up_new_fragments
  - tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one
  - tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog_fragment
- text: Given a worktree attempting to hand-edit a land-owned release artifact, when
    it commits, then the existing guard still refuses, proving the fix did not weaken
    artifact ownership.
  evidence:
  - tests/test_release.py::TestChangelogFragments::test_write_then_read_round_trips
  - tests/test_release.py::TestChangelogFragments::test_read_sorts_numerically_not_lexically
  - tests/test_release.py::TestChangelogFragments::test_read_fails_closed_on_a_malformed_fragment
  - tests/test_release.py::TestChangelogFragments::test_assemble_writes_every_fragment_as_a_bullet
  - tests/test_release.py::TestChangelogFragments::test_assemble_is_idempotent_and_picks_up_new_fragments
  - tests/test_ticket_land.py::TestRealCallbackStaleWorktreeManifest::test_stale_worktree_manifest_still_lands_main_plus_one
  - tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook::test_land_owned_file_commit_refused_changelog_fragment
threat: null
component: release
anchor: false
anchor_reason: null
land_commit: 28e240dc8f2d4d441599cf314f7b981ae9efe9a3
---
Every land writes the SAME two shared files, so any two concurrent lands
conflict on them by construction -- independent of what code the tickets
actually touch.

MEASURED over the last 40 commits (7 of which are land commits):

    land commits touching CHANGELOG.md:    6 of 7
    land commits touching pyproject.toml:  6 of 7   (the version line)

REPORTED COST, from an agent that hit it three times in one series:
"Each land collided with a concurrent land from another agent touching
the shared CHANGELOG.md/version-bump mechanism (T-2406, then T-2400
twice), each requiring a manual conflict-resolve-and-rebump cycle before
retrying. This consumed most of the available turn budget for two
tickets." That agent completed 2 of 9 planned children, and the
collisions -- not the work -- are what stopped it.

WHY THIS IS THE THROUGHPUT CEILING. Scope-disjointness is the property
this fleet is organised around: agents are dispatched on non-overlapping
file scopes precisely so their lands do not collide. The release-artifact
mechanism defeats that entirely, because it makes EVERY land touch a
common path. Two perfectly disjoint tickets still serialize, and worse,
they serialize with a MANUAL resolve step rather than a clean queue.
Current observed throughput is ~5 lands/hour against a ~12/hour target,
and this is a substantial part of the gap.

It also compounds a known hazard: CHANGELOG.md is land-owned, worktree
edits to it are silently discarded by the release-artifact reset, and a
concurrent land can clobber a direct main commit. So the file that every
land must touch is also one with unusually sharp edges.

FIX SHAPE -- design judgement wanted, several viable directions:
  - Make the version bump and CHANGELOG entry a POST-MERGE step derived
    from the landed commits, rather than content each land carries in
    its own branch. Nothing to conflict on if nobody writes it in a
    worktree.
  - Or make the CHANGELOG append-only per ticket (a fragment file per
    ticket id, e.g. `changelog.d/T-####.md`, assembled at release time).
    This is the standard solution to exactly this problem -- towncrier
    and friends exist because every project with concurrent merges hits
    it -- and fragments never conflict because no two tickets write the
    same path.
  - Or serialize ONLY the artifact step behind the existing land lock
    while letting the expensive verification run concurrently. Weaker,
    but far cheaper to build.
The fragment-per-ticket approach is my recommendation; the ticket id
already gives a natural unique filename and this repo already thinks in
per-ticket directories (`tickets/T-####/`).

POSITIVE CONTROLS:
  - must-now-succeed: two lands whose code scopes are disjoint complete
    without a manual CHANGELOG/version conflict-resolution step. This is
    the whole point; assert on it directly.
  - must-still-produce: a release still emits a complete, correctly
    ordered CHANGELOG containing every landed ticket's entry, and the
    version still bumps exactly once per release. Do not fix the
    conflict by dropping entries -- an incomplete changelog is worse
    than a slow one.
  - must-still-refuse: whatever guard currently prevents a worktree from
    hand-editing land-owned release artifacts must remain effective.