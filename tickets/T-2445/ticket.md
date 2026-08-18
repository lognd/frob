---
id: T-2445
title: every land writes CHANGELOG.md and the version line, so scope-disjoint lands
  still conflict
state: queued
kind: bug
origin: human
created: '2026-08-18'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
acceptance:
- text: Given two lands whose declared code scopes are disjoint, when both run, then
    neither requires a manual CHANGELOG or version conflict-resolution step.
  evidence: []
- text: Given a release cut after several concurrent lands, when the CHANGELOG is
    produced, then it contains every landed ticket's entry in correct order and the
    version bumped exactly once, proving conflicts were not resolved by dropping entries.
  evidence: []
- text: Given a worktree attempting to hand-edit a land-owned release artifact, when
    it commits, then the existing guard still refuses, proving the fix did not weaken
    artifact ownership.
  evidence: []
threat: null
component: release
anchor: false
anchor_reason: null
land_commit: null
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
