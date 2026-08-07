---
id: T-1349
title: Verify the mutation evidence T-1334 skipped on the split land modules
state: done
kind: bug
origin: agent
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/_land_release.py
- src/frob/tickets/_land_squash.py
- tests/test_ticket_land.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_read_root_manifest_version_ok_but_nonzero_returncode_is_none
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_monotonic_when_no_prior_version
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_equal_versions_not_monotonic
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_lesser_version_not_monotonic
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_greater_version_is_monotonic
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_log_monotonicity_refusal_fires_on_genuine_desync
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed
- tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_land_commit_details_diff_tree_fails_returns_empty_files
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_scoped_content_matches_worktree_head_err_is_false
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_verified_false_when_ticket_not_done
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_verified_false_when_load_fails
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_report_stacked_sibling_absorption_reports_real_land_not_dry_run
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorbed_land_report_none_when_staged_files_nonempty
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_staged_files_diff_ok_but_nonzero_returncode_is_failed
- tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha
designated_repro_test: null
acceptance:
- text: given the split land modules, when the mutation harness runs, then every surviving
    mutant is either killed by a new test or individually justified by name
  evidence:
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_read_root_pyproject_version_ok_but_nonzero_returncode_is_none
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_read_root_manifest_version_ok_but_nonzero_returncode_is_none
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_monotonic_when_no_prior_version
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_equal_versions_not_monotonic
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_lesser_version_not_monotonic
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_fallback_path_greater_version_is_monotonic
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_log_monotonicity_refusal_quartet_desync_requires_all_three_legs
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_log_monotonicity_refusal_fires_on_genuine_desync
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_sync_uv_lock_ok_but_nonzero_returncode_on_git_add_is_failed
  - tests/test_ticket_land.py::TestLandReleaseMonotonicityHelpers::test_resync_release_manifest_ok_but_nonzero_returncode_on_git_add_is_failed
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_worktree_full_changeset_diff_ok_but_nonzero_returncode_is_failed
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_land_commit_details_diff_tree_fails_returns_empty_files
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_scoped_content_matches_worktree_head_err_is_false
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_scoped_content_matches_diff_ok_but_nonzero_is_false
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_verified_false_when_ticket_not_done
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorption_verified_false_when_load_fails
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_report_stacked_sibling_absorption_reports_real_land_not_dry_run
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_absorbed_land_report_none_when_staged_files_nonempty
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_staged_files_diff_ok_but_nonzero_returncode_is_failed
  - tests/test_ticket_land.py::TestLandSquashHelpersMutationCoverage::test_land_commit_details_rev_parse_ok_but_nonzero_returncode_is_no_sha
threat: null
component: tickets
---
T-1334 (split of _land_finalize.py into _land_squash.py + _land_release.py, landed 6687c6dd) was landed with "--skip-mutation-evidence" to get past a TEST016 EvidenceConfirmatoryOnly warning on the new src/frob/tickets/_land_release.py.

The stated justification was reasonable as far as it goes: the code was MOVED, not newly authored, and the pre-existing tests already cover it structurally, so the mutation harness was flagging non-killed mutants on relocated code. That is the documented WARN-level shape.

But it is still a strictness weakening applied to the LAND MACHINERY ITSELF -- the code path every other agent depends on to land work correctly, and the subject of repeated silent-regression incidents in this repo's history (dropped code, dropped ledger blocks, false-green lands). "The tests cover it structurally" is exactly the claim mutation testing exists to falsify, so accepting it unverified on this particular module is the least appropriate place to do so.

WORK: run the mutation harness against src/frob/tickets/_land_release.py (and _land_squash.py, same split, same reasoning) and either
  (a) confirm the surviving mutants are genuinely unmutable-semantics lines, and record that finding with the specific mutants named, or
  (b) write the tests that kill them.
Do NOT simply re-assert the structural-coverage claim -- the point of this ticket is to check it.

Context: per this repo's standing rule, a completion claim needs a passing gate, not prose. See the "catalogued is not enforced" principle.