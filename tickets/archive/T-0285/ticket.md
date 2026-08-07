---
id: T-0285
title: 'coverage: land/tickets/lint/vet/dup TEST005 zero'
state: done
kind: bug
origin: agent
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/tickets/**
- src/frob/strata/_lint.py
- src/frob/vet/_capability.py
- src/frob/dup/_cache.py
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_land.py::TestCloseFailAfterMerge::test_close_fails_after_merge_when_main_dropped_same_id
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_main_dirty_check_git_failure
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_main_branch_lookup_failure
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_wip_commit_status_check_failure
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_merge_command_failure
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_unowned_deletions_diff_failure_after_merge
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_squash_command_failure
- tests/test_ticket_land.py::TestGitSubprocessFailures::test_final_commit_failure
- tests/test_ticket_land.py::TestLandDeeperBranches::test_unowned_deletion_real_run_with_actual_merge
- tests/test_ticket_land.py::TestLandDeeperBranches::test_post_merge_commit_failure
- tests/test_ticket_land.py::TestLandDeeperBranches::test_finalize_draft_failure
- tests/test_ticket_land.py::TestLandDeeperBranches::test_worktree_branch_lookup_failure_after_close
- tests/test_ticket_land.py::TestLandNotFound::test_unknown_ticket_id_returns_not_found
- tests/test_ticket_land.py::TestWipCommit::test_dry_run_wip_commits_uncommitted_changes
- tests/test_ticket_land.py::TestWipCommit::test_real_land_wip_commits_uncommitted_changes
- tests/test_ticket_land.py::TestKindEvidenceMismatch::test_non_docs_kind_with_cmd_evidence_refused
- tests/test_ticket_land.py::TestUnownedDeletionRealRun::test_unowned_deletion_aborts_on_real_run
- tests/test_ticket_land.py::TestMergeConflictOutsideLedger::test_real_conflict_outside_tickets_md_aborts
- tests/unit/strata/test_lint.py::TestRateBaseDimensionMismatch::test_unknown_unit_propagates_unknown_unit_error
- tests/unit/strata/test_lint.py::TestLintFaninCapacityNoInboundFlows::test_capacitied_node_with_no_rated_inbound_flow_is_clean
- tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_same_digest_and_rung_overwrites_prior_payload
- tests/unit/test_dup_cache.py::TestFingerprintRoundTrip::test_connect_error_is_propagated_without_writing
- tests/test_capability_registry.py::TestIsSelfPatternPath::test_root_not_frob_repo_returns_false
designated_repro_test: null
threat: null
component: null
---
## Description

The coverage stamp flagged below-floor TEST005 (unit_branch_cov=90,
module_line_cov=85) for six functions across five files:
`src/frob/tickets/_land.py::land` (71% branch, module 72.7% line),
`src/frob/tickets/__init__.py::run_cmd_evidence` (75%) and
`::add_cmd_evidence` (89.5%), `src/frob/strata/_lint.py::evaluate_lint`
(76.9%) and `::check_lint_fanin_capacity` (87.5%),
`src/frob/vet/_capability.py::is_self_pattern_path` (77.8%), and
`src/frob/dup/_cache.py::put_fingerprint` (87.5%).

## Plan

Write real, branch-covering pytest tests exercising the actual uncovered
branches per function (land's abort/error paths -- dirty-main,
deletion-filter-abort, close-fail-after-merge, git-subprocess-failure
early returns, the archive-aware splice; run_cmd_evidence/add_cmd_evidence's
launch-failure and load/write-failure propagation; _lint's per-rule
dimension-mismatch and short-circuit branches; is_self_pattern_path's
foreign-vs-self discriminator and OSError branch; put_fingerprint's
cache-hit-overwrite and connect-error branches), never lowering
`frob.toml` thresholds.