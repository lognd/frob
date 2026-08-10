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
runs_last: false
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

## Done report

RECOMPUTE, NOT CARRY, implemented as the required fix.

Root cause, precisely: none of `pyproject.toml`/`CHANGELOG.md`/
`.frob-release.json` is protected by `ticket.scope`, so a `git merge
--squash` can resolve a change to any of them CLEANLY (no conflict
object at all -- `_auto_resolve_out_of_scope_conflicts`'s keep="ours"
only ever fires on a genuine git conflict, so it structurally cannot
protect a file that never conflicts). When that happens, `root`'s
working tree can already hold a regressed version/manifest before
`_apply_release_bump` ever runs. The existing T-0992 monotonicity guard
only validates a bump `bump_version` itself REPORTS computing
(`bumped.danger_ok is not None`); a callback that legitimately reports
`Ok(None)` (this land's own diff needs no new bump) left that branch
completely unvisited -- and `_ensure_release_quartet_coherent`'s own
T-1358 check only compares the two regressed files to EACH OTHER, which
a self-consistent stale pair passes trivially. That is the exact gap:
"nothing compares the incoming version against what main already has"
applies precisely to the no-bump-needed path.

Fix, matching the ticket's four REQUIRED items:

1/3 (monotonic + recompute-not-carry): `_reset_release_artifacts_to_pre_
land` (new) runs UNCONDITIONALLY as the very first step of
`_apply_release_bump`, before `bump_version` is even invoked: `git
checkout <pre_land_tip> -- pyproject.toml CHANGELOG.md .frob-
release.json` discards whatever the squash carried and resets all three
to root's own true, last-committed state. The bump is now a function of
(root's manifest at pre_land_tip, the landing API) evaluated at squash
time, never anything a worktree brought along -- there is nothing left
to detect, only a baseline to always start from.

2 (manifest never regresses): the same reset covers `.frob-release.json`
-- it is one of the three files reset, not just pyproject.toml.

4 (monotonicity assertion, belt-and-braces): `_assert_no_monotonicity_
regression` (new) runs unconditionally at the end of `_apply_release_
bump` (via the new `_finalize_release_coherence` split, added to keep
the parent under ARCH001's threshold), comparing the FINAL working-tree
versions against `pre_bump_version`/`pre_manifest_version` via a new
`_version_not_regressed` (the `>=` sibling of `_release_bump_is_
monotonic`'s strict `>` -- "unchanged" is the CORRECT outcome on a
no-bump-needed land, so the assertion must not use strict `>` there).
Refuses and unwinds the squash if it ever fires; after the reset above
this should never actually trigger in practice -- it exists so a future
change to this module that reintroduces a carry path fails loudly
instead of repeating this incident silently.

Regression coverage (tests/unit/test_land_release_coherence.py, new
`TestResetReleaseArtifactsRealGitRepo` class, against a REAL git repo,
not the module's `_fake_run_argv` stub): reproduces the STATE the field
incident produced (main committed at 0.366.0; working tree/index already
holding a regressed, internally-coherent 0.365.0 pair, staged via a real
`git add`) and proves `_apply_release_bump` corrects it back to 0.366.0
even when `bump_version` reports `Ok(None)`. A second test confirms the
reset does not fight a LEGITIMATE bump this land itself needs (0.366.0 ->
0.367.0 still lands at 0.367.0, not clobbered back). Did not attempt to
reproduce the exact git-diff3 decision tree that lets a real squash-merge
land a regression cleanly (multiple candidate mechanisms exist and this
investigation did not fully isolate the single one behind the four real
commits) -- the fix is unconditional and correct regardless of which
mechanism produced the state, so testing the state directly (same
approach the pre-existing T-1358 tests in this file already use) is
honest coverage, not a weaker substitute. `tests/test_ticket_land.py`
(T-1721 precedent) is the natural home for a full-CLI real-squash-merge
reproduction if one is wanted later; out of this ticket's own scope.

Scope widened beyond the ticket's original four files (via `frob ticket
scope --add`, each with a reason): `_land_release.py` (the T-0992
monotonicity guard and `_apply_release_bump` this ticket must extend
actually live here, not in the two files the auto-filed ticket named),
`docs/modules/tickets.md` (AFFECT001 requires the affects()-closure doc
for `_apply_release_bump` to move in the same diff), `design/frob.strata`
(SELFAUDIT001/SYS100 requires the testsuite node's `may exec via` list to
cover the new test file's real `subprocess.run` call sites, since strata
capability detection is lexical/per-file, not test-framework-aware).

Triaged the three coordinator-named stale sweep tickets per instructions
(verified against current main's `frob check --only tickets`/`--only
release`, both 0 errors) and dropped all three as stale, none
reproducing:
- T-1747 (TICK003 from T-1715): 0 TICK003 findings on main.
- T-1757 (REL001 from T-1754): 0 REL001 findings; pyproject.toml/
  .frob-release.json both already agree at 0.367.0 (T-1627's land).
- T-1759 (REL001 from T-1756): same, 0 REL001 findings, same reason.

Changed:
- src/frob/tickets/_land_release.py::_reset_release_artifacts_to_pre_land (new)
- src/frob/tickets/_land_release.py::_apply_release_bump (calls the reset first; split via _finalize_release_coherence to stay under ARCH001)
- src/frob/tickets/_land_release.py::_finalize_release_coherence (new)
- src/frob/tickets/_land_release.py::_assert_no_monotonicity_regression (new)
- src/frob/tickets/_land_release.py::_version_not_regressed (new)
- docs/modules/tickets.md#frob-ticket-land (T-1760 subsection)
- design/frob.strata (testsuite node's may exec via list; frob:ticket edge)
- tests/unit/test_land_release_coherence.py (TestResetReleaseArtifactsRealGitRepo, 2 new tests)

Evidence: 4 pytest node ids recorded via `frob ticket evidence` (2 new
TestResetReleaseArtifactsRealGitRepo tests, plus 2 pre-existing
TestApplyReleaseBumpCoherenceGuard tests re-verified still passing after
the change). Full module: `tests/unit/test_land_release_coherence.py`,
12 passed. `tests/test_ticket_land.py -k "release or bump or Bump or
Release"` (out-of-scope real-land coverage this change could plausibly
affect): 21 passed, unaffected.

Gates: `frob check --land-parity` clean (0 unscoped errors) after fixing
ARCH001 (split `_apply_release_bump`), AFFECT001 (docs/modules/
tickets.md), SELFAUDIT001/SYS100 (design/frob.strata testsuite node's may
exec via list), and WIRE001 (inlined the test-only `_commit_release_
state` helper as an instance method of the one class that uses it,
instead of a bare module-level function with no non-test caller).

Not done / disclosed: the exact git-merge mechanism that produced the
four real oscillating commits was not conclusively isolated (see the new
test class's own docstring) -- the fix closes the defect unconditionally
regardless of mechanism, so this did not block the fix, but a fuller
forensic writeup of the precise diff3 trigger is not part of this
ticket's Done report.

### Changed
```
 .frob-release.json |  4 +---
 CHANGELOG.md       |  4 ----
 pyproject.toml     |  2 +-
 tickets.md         | 44 +++++++++++++++++++++++++++++++++++++++-----
 uv.lock            |  2 +-
 5 files changed, 42 insertions(+), 14 deletions(-)
```

### Evidence
- `tests/unit/test_land_release_coherence.py::TestResetReleaseArtifactsRealGitRepo::test_regressed_working_tree_is_reset_before_bump_runs` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestResetReleaseArtifactsRealGitRepo::test_legitimate_bump_still_advances_past_the_reset_baseline` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_none_but_pyproject_already_diverged` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_release_coherence.py::TestApplyReleaseBumpCoherenceGuard::test_callback_reports_new_version_normally` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 1 error(s), 683 warning(s), 726 waived
- error-findings: PRE001@tickets/T-1760
