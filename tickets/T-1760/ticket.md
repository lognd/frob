---
id: T-1760
title: A land carries stale release artifacts onto main and reverts a sibling's version
  bump; the version is not monotonic
state: done
kind: bug
origin: agent
created: '2026-08-07'
priority: critical
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/tickets/_land_finalize.py
- src/frob/release/__init__.py
- tests/unit/test_land_release_coherence.py
- src/frob/tickets/_land_release.py
- docs/modules/tickets.md
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/tickets/_land_release.py
  reason: the T-0992 monotonicity guard and _apply_release_bump/_ensure_release_quartet_coherent
    this ticket must extend live in _land_release.py (split out of _land_finalize.py
    by T-1251); the fix cannot be made without touching the file that actually holds
    the guard it must close the gap in
  actor: logan
  at: '2026-08-07'
- op: add
  glob: docs/modules/tickets.md
  reason: AFFECT001 requires the affects()-closure doc (docs/modules/tickets.md#frob-ticket-land)
    to move in the same diff as _apply_release_bump, which this ticket must change
  actor: logan
  at: '2026-08-07'
- op: add
  glob: design/frob.strata
  reason: SELFAUDIT001/SYS100 requires the testsuite node's may exec via list to cover
    the new test file's real subprocess.run call sites
  actor: logan
  at: '2026-08-07'
evidence:
- tests/unit/test_land_release_coherence.py::TestResetReleaseArtifactsRealGitRepo::test_regressed_working_tree_is_reset_before_bump_runs
- tests/unit/test_land_release_coherence.py::TestResetReleaseArtifactsRealGitRepo::test_legitimate_bump_still_advances_past_the_reset_baseline
- tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_none_but_pyproject_already_diverged
- tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_new_version_normally
designated_repro_test: null
threat: null
component: null
---
A land carries its worktree's copy of the release artifacts onto main and
OVERWRITES a newer bump that landed in between. The version does not
advance monotonically -- it oscillates.

Measured on main, four consecutive land commits:

    1647eb98 (T-1692)  version = "0.366.0"   manifest 0.366.0
    92a1dea0 (T-1754)  version = "0.365.0"
    e2a5124d (T-1755)  version = "0.366.0"
    0f436d9c (T-1756)  version = "0.365.0"   manifest 0.365.0

Main now declares 0.365.0 while REL001 requires >= 0.366.0, so the gate
is RED and stays red until someone bumps by hand. The recorded API
manifest is stale by the same amount, which is worse than the version
string: `.frob-release.json` is the baseline every future REL001
comparison is measured against, so a reverted manifest silently changes
what counts as an API change from then on.

MECHANISM. `_apply_release_bump_for_land` computes the required bump
against ROOT's manifest at land time and writes pyproject.toml,
CHANGELOG.md and .frob-release.json into the branch being landed. The
squash-apply then carries those files onto main. When a worktree was
branched BEFORE a sibling's bump landed, its copies still hold the older
version, and the squash overwrites main's newer values with them. Nothing
compares the incoming version against what main already has.

This is the release-artifact analogue of T-1721 (the ledger splice
silently dropping a sibling's edit) and it has the same shape: a
last-writer-wins overwrite of shared state, with no comparison against
what is already there and no refusal when the two disagree.

REQUIRED:

1. THE VERSION MUST BE MONOTONIC AT LAND. Before the squash carries the
   release artifacts, compare the incoming version against main's
   current. If incoming < current, do not overwrite -- recompute the bump
   from main's actual state, or refuse and say so. A land must never move
   the declared version backwards.
2. THE SAME FOR THE MANIFEST. `.frob-release.json` is the REL001
   baseline; regressing it corrupts every subsequent comparison. Treat it
   as strictly append-forward: main's recorded API surface may gain
   entries from a land, never lose them to a stale copy.
3. RECOMPUTE, DO NOT CARRY. The cleanest fix is for the land to compute
   and write the release artifacts against ROOT's state at the moment of
   the squash, rather than carrying artifacts written earlier in the
   worktree. The bump is a function of (main's manifest, the landing
   API); it should be evaluated where main is, not where the worktree
   was.
4. Add a gate or land-time assertion that main's declared version is
   never less than its own manifest's, and never less than the previous
   commit's. A silent backwards move is currently invisible -- it
   surfaced here only because REL001 went red afterwards and someone
   read four commits of history.

REGRESSION COVERAGE must reproduce the real shape: two worktrees branched
from the same base, land A (bumps to X+1), then land B (branched before
A, carrying X). Assert main still declares X+1 afterwards, and that the
manifest did not regress.

Note for whoever takes this: T-1740 fixed land leaving its staged
artifacts behind on refusal. This is the sibling defect on the SUCCESS
path -- the artifacts are applied, just from the wrong baseline.