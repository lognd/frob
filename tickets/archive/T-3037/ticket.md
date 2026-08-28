---
id: T-3037
title: stale ticket-minting test fixture trips T-2394 empty-scope guard (28 tests)
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_work_and_land_finish.py
- tests/test_ticket_runner_archive_force.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket
- tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness
- tests/test_ticket_work_and_land_finish.py::TestWork::test_no_fleet_context_does_not_claim_an_xdist_bound
- tests/test_ticket_work_and_land_finish.py::TestWork::test_prints_the_agent_env_eval_line_naming_the_worktree
- tests/test_ticket_work_and_land_finish.py::TestWork::test_fleet_context_reports_the_bound_agent_env_exports_computed
- tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_removes_worktree_and_deletes_its_branch
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_unverified_land_exits_nonzero_even_without_finish
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_refuses_and_touches_nothing_when_unverified
- tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
- tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 0fe5f273fb6fc764233dc3a125d19d4af5f2dd8b
---
Linux full-suite triage (T-2992): a cluster of 28 ticket-lifecycle CLI
round-trip tests fail, all sharing the shape "create a fresh ticket via
a test helper, then run a real ticket-runner CLI verb against it in a
scratch git repo". Root cause CONFIRMED in one sample
(test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket):

  ERROR ticket start failed: T-0001 has an EMPTY scope -- either add
  scope (`frob ticket scope T-0001 --add '<glob>' --reason '...'`) or,
  if this ticket legitimately has no file scope ..., declare that
  explicitly: `frob ticket scope T-0001 --declare-no-scope --reason
  '...'`

This is T-2394's empty-scope start-refusal guard doing its job -- the
shared test fixture/helper these 28 tests use to mint a throwaway ticket
predates that guard and never sets a scope (or declares no-scope) before
calling `frob ticket start`/`frob ticket work`. Every one of these 28
tests is presumably fine on the actual PRODUCT side; this is TEST
fragility from a stale shared fixture, not (confirmed so far) a product
regression.

CONFIRMED (1): the sample above.
LIKELY SAME ROOT CAUSE (27, by shared "mint-a-ticket-then-run-CLI-verb"
shape -- NOT individually re-run/confirmed, verify each before assuming):
  tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness
  tests/test_ticket_work_and_land_finish.py::TestWork::test_no_fleet_context_does_not_claim_an_xdist_bound
  tests/test_ticket_work_and_land_finish.py::TestWork::test_prints_the_agent_env_eval_line_naming_the_worktree
  tests/test_ticket_work_and_land_finish.py::TestWork::test_fleet_context_reports_the_bound_agent_env_exports_computed
  tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_cli_land_end_to_end_refuses_a_worktree_with_a_real_ty_error
  tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
  tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_cli_land_invoked_with_root_equal_to_worktree_still_verifies
  tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree
  tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land
  tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_removes_worktree_and_deletes_its_branch
  tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_unverified_land_exits_nonzero_even_without_finish
  tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_retire_on_proof_refuses_and_touches_nothing_when_unverified
  tests/test_ticket_work_and_land_finish.py::TestBranchDriftGuard::test_branch_drift_before_final_commit_refuses_by_construction
  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_with_no_live_leases_stays_quiet
  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_refuses_without_force_when_a_live_lease_exists
  tests/test_ticket_runner_archive_force.py::TestTicketArchiveForceCLI::test_force_overrides_the_live_lease_refusal
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_start_auto_plans_queued_ticket
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_without_evidence_fails
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow
  tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true
  tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged
  tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected
  tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree
  tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report
  tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
  tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean

FIX DIRECTION (not applied here -- pure triage/filing ticket per T-2992's
own acceptance): find the shared ticket-minting test helper(s) these
files use (likely a `_new_ticket`/`_make_ticket` fixture in a shared
conftest or per-file helper) and either give it a real scope glob or
call `frob ticket scope --declare-no-scope` before `start`/`work`. Given
the size of this cluster, a single shared-fixture fix may clear most of
it in one change -- but each listed id above needs individual re-run
after the fix to confirm, since only 1 was directly reproduced here.