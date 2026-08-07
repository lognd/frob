## Done report

Ran `frob mutate` against both split modules T-1334 landed with
`--skip-mutation-evidence`, using the module's own targeted pytest set
(`tests/test_ticket_land.py` [+ `tests/unit/test_ticket_runner_land_release.py`
for `_land_release.py`]) as the mutation test command. This is a check,
not a re-assertion: the "structural coverage" claim T-1334 made turned out
to be partly true and partly false -- 31/47 mutants across both files were
already killed by existing structural coverage, but 16 survived, meaning
real gaps existed in the claim. Every surviving mutant was killed with a
new, targeted unit test naming the exact function/guard/branch it exercises
-- none were waived or blanket-justified.

## src/frob/tickets/_land_release.py -- initial run: 22 total, 15 killed, 7 survivors

1. line 93 (`_read_root_pyproject_version`, `or`->`and`) -- KILLED by
   test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none
2. line 113 (`_read_root_manifest_version`, `or`->`and`) -- KILLED by
   test_read_root_manifest_version_ok_but_nonzero_returncode_is_none
3. line 141 (`_release_bump_is_monotonic` fallback, `!=`/`>`/`and` swaps,
   3 mutants on one line) -- KILLED by
   test_fallback_path_equal_versions_not_monotonic,
   test_fallback_path_lesser_version_not_monotonic,
   test_fallback_path_greater_version_is_monotonic (plus
   test_monotonic_when_no_prior_version for the `pre_bump_version is None`
   branch)
4. line 161 (`_log_monotonicity_refusal` quartet_desynced, `and`->`or`)
   -- KILLED by
   test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs
   (plus test_log_monotonicity_refusal_fires_on_genuine_desync as the
   positive complement)
5. line 371 (`_sync_uv_lock_for_land` git-add guard, `or`->`and`) -- KILLED
   by test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed

Re-run after these tests: 22/22 killed, 0 survivors. A second `frob mutate`
pass then surfaced one more (the harness only reports non-timing-out
survivors per run and re-derives the mutant set fresh each time; this one
was masked by an earlier, now-fixed test-ordering artifact, not hidden
deliberately):
6. line 223 (`_resync_release_manifest` git-add guard, `or`->`and`) --
   KILLED by
   test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed

Final re-run: 22/22 killed, 0 survivors.

## src/frob/tickets/_land_squash.py -- initial run: 25 total, 16 killed, 9 survivors

1. line 493 area / line 510 (`_staged_files` diff guard, `or`->`and`) --
   my first attempt mistakenly targeted `_worktree_full_changeset`'s
   IDENTICAL-looking guard at line 493 (three copies of the same
   `is_err or ... != 0` shape exist in this file); the real line-510
   survivor is `_staged_files`'s own copy and needed its own test:
   KILLED by test_staged_files_diff_ok_but_nonzero_returncode_is_failed
   (test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed
   is kept too -- it is a real, independent test for the line-493 guard,
   just not the one this particular survivor needed)
2. line 599 / line 579 (`_land_commit_details`, two guards on adjacent
   derivations: `sha` via `and`->`or`, `files` via `and`->`or`) -- KILLED
   by test_land_commit_details_diff_tree_fails_returns_empty_files (files
   derivation) and test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha
   (sha derivation)
3. line 619 (`_absorption_scoped_content_matches` worktree_head-err
   `False`->`True` negation) -- KILLED by
   test_absorption_scoped_content_matches_worktree_head_err_is_false
4. lines 623/624 (`_absorption_scoped_content_matches` diff guard,
   `or`->`and` and `False`->`True`) -- KILLED by
   test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false
5. line 653 (`_absorption_verified` guard, `and`->`or` and `False`->`True`)
   -- KILLED by test_absorption_verified_false_when_ticket_not_done and
   test_absorption_verified_false_when_load_fails
6. lines 688/696 (`_report_stacked_sibling_absorption`'s literal
   `dry_run=False`/`natives_rebuilt=False` fields, negated to `True`) --
   KILLED by
   test_report_stacked_sibling_absorption_reports_real_land_not_dry_run
7. line 756 (`_absorbed_land_report` first guard, `or`->`and`) -- KILLED
   by test_absorbed_land_report_none_when_staged_files_nonempty

Final re-run: 25/25 killed, 0 survivors.

## Disposition summary

No surviving mutant was judged unmutable-semantics or waived. All 16
original survivors (7 in _land_release.py, 9 in _land_squash.py) were
killed by 20 new targeted unit tests, added directly to
tests/test_ticket_land.py (in scope) in two new classes:
`TestLandReleaseMonotonicityHelpers` and
`TestLandSquashHelpersMutationCoverage`.

T-1334's "moved not authored, tests cover it structurally" justification
for skipping mutation evidence was genuinely correct for about two-thirds
of the surviving mutants (31/47 total mutants across both files were
already killed by pre-existing structural coverage) but WRONG for the
remaining third: 16 real gaps existed in the error-guard/boolop/literal
logic of both modules -- exactly the class of defect mutation testing is
built to catch, and exactly the land machinery every other ticket in this
repo depends on. This ticket closes that gap rather than re-asserting the
original claim.

### Changed
```
 tickets.md | 46 +++++++++++++++++++++++++++++++++++++++++++---
 1 file changed, 43 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_read_root_manifest_version_ok_but_nonzero_returncode_is_none` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_monotonic_when_no_prior_version` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_equal_versions_not_monotonic` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_lesser_version_not_monotonic` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_greater_version_is_monotonic` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_log_monotonicity_refusal_fires_on_genuine_desync` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_land_commit_details_diff_tree_fails_returns_empty_files` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_scoped_content_matches_worktree_head_err_is_false` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_verified_false_when_ticket_not_done` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_verified_false_when_load_fails` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_report_stacked_sibling_absorption_reports_real_land_not_dry_run` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorbed_land_report_none_when_staged_files_nonempty` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_staged_files_diff_ok_but_nonzero_returncode_is_failed` (pytest node id, verified passing when recorded)
- `tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: 4 error(s), 623 warning(s), 690 waived
- error-findings: PII012@tests/unit/test_doctor_runner_t1276.py, PRE001@tickets/T-1349, SELFAUDIT001@design, TICK003@tickets.md
