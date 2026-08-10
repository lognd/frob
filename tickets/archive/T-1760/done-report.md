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
