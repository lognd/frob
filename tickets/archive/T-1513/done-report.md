## Done report

The post-land Tier-A cleanup commit in _sweep_apply_tier_a_and_commit used
git add -A + a plain git commit. Because uv.lock (and other land-owned
files) is perpetually dirty in a worktree, git add -A staged it alongside
the real Tier-A fix; the T-0731 pre-commit hook then refused the commit,
leaving the fix uncommitted and the re-scan seeing the same errors, so
land reverted every time this path was exercised.

Fixed by:
- _apply_root_tier_a_fixes now returns the sorted, de-duplicated list of
  repo-relative paths Tier-A actually rewrote (was a bare int count),
  giving the caller the exact path set to stage.
- _sweep_apply_tier_a_and_commit now runs `git add -- <exact paths>`
  instead of `git add -A`, so a land-owned file dirty for unrelated
  reasons can never be swept into this commit.
- The commit itself now runs under the existing FROB_LAND_INTERNAL=1
  context manager (_land_internal_git_env, T-0828's escape hatch) since
  this is land's own internal commit -- same disposition as land's other
  internal commits -- so a Tier-A fix that happens to touch a land-owned
  file is not itself refused.
- Both the add and commit failure paths now log git's stderr via
  _describe_git_failure instead of staying silent.

Unit tests added/updated in
tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep:
the existing fixed-by-tier-a test was updated for the new list-returning
signature, and a new test
(test_fix_commit_stages_only_touched_paths_not_git_add_dash_a) asserts an
unrelated dirty file present alongside the Tier-A fix is NOT staged or
committed by the follow-up cleanup commit, and remains dirty afterward.

### Changed
```
 src/frob/app/ticket_runner/_land_cmd.py   | 92 ++++++++++++++++++++-----------
 tests/test_ticket_work_and_land_finish.py | 56 ++++++++++++++++++-
 tickets.md                                |  6 +-
 3 files changed, 119 insertions(+), 35 deletions(-)
```

### Evidence
- `tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_fix_commit_stages_only_touched_paths_not_git_add_dash_a` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 130 warning(s), 770 waived
- error-findings: none (measured, zero errors)
