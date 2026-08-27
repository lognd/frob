---
id: T-3080
title: Remaining T-2394 empty-scope fixture drift (10 tests, T-3037 residue)
state: done
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land_proof_claims.py
- tests/test_ticket_evidence.py
- tests/system/test_cli_ticket.py
- tests/system/test_cli_ticket_promote.py
- tests/test_ticket_leases.py
- tests/system/test_cli_ticket_land.py
- tickets/T-3098/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tickets/T-3098/**
  reason: 'T-3080 filed a follow-up ticket (T-3098) for an unrelated pre-existing
    test-exhaustiveness regression found while re-verifying this ticket''s own touched-set
    tests; the filed ticket''s own directory is a byproduct of that filing, not code
    this ticket modifies.

    '
  actor: logan
  at: '2026-08-27'
- op: add
  glob: tickets/T-3098/**
  reason: 'T-3080 filed a follow-up ticket (T-3098) for an unrelated pre-existing
    test-exhaustiveness regression found while re-verifying this ticket''s own touched-set
    tests; the filed ticket''s own directory is a byproduct of that filing, not code
    this ticket modifies.

    '
  actor: logan
  at: '2026-08-27'
evidence:
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected
- tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree
- tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_start_auto_plans_queued_ticket
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_without_evidence_fails
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds
- tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow
- tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean
- tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean
designated_repro_test: tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Split off from T-3037 (whose own scope covered only tests/test_ticket_
work_and_land_finish.py and tests/test_ticket_runner_archive_force.py):
the SAME root cause -- a stale ticket-minting test helper that predates
the T-2394 empty-scope `frob ticket start` guard and never sets a scope
(or declares no-scope) -- also trips these node ids (from T-3037's own
triage list, individually confirmed or "likely same shape" per its own
body):

  tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true
  tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged
  tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected
  tests/test_ticket_evidence.py::TestEvidenceCmdCwd::test_relative_probe_only_succeeds_from_worktree
  tests/system/test_cli_ticket_promote.py::TestPromoteCLI::test_promotes_a_draft_carrying_evidence_and_done_report
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_start_auto_plans_queued_ticket
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_without_evidence_fails
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_close_with_evidence_and_done_report_succeeds
  tests/system/test_cli_ticket.py::TestTicketRoundTrip::test_plan_then_sweep_flow
  tests/test_ticket_leases.py::TestCommitFullLedgerChange::test_archive_cli_leaves_repo_clean

Re-confirmed live (2026-08-27): all 10 above still fail at HEAD with the
same "T-#### has an EMPTY scope" refusal from `frob ticket start`.
`tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_
clean` ALSO fails, but at a DIFFERENT, later guard (T-2114 new-public-
symbol doc/test-edge check on a fixture file `src/new_thing.py`) once the
empty-scope refusal is worked around -- needs its own look, not
necessarily the same fixture-drift shape; note it here so it is not lost
but do not assume it is covered by this ticket's fix pattern without
re-checking.

FIX DIRECTION (same as T-3037's landed fix): find each file's own
ticket-minting helper and give it a real scope glob matching a file the
fixture repo actually creates, OR (T-3037's own preferred shape) mint via
`new_ticket`/CLI `new` and then follow up with `set_no_scope_declared`/
`frob ticket scope --declare-no-scope` when the test genuinely needs an
empty scope. T-3037 also filed a follow-up bug (this repo's ticket
tracker; see T-3037's Done report for the id) for `_ticket_from_spec`
silently dropping `TicketSpec.no_scope_declared`/`no_scope_declared_
reason` -- that bug means the direct `TicketSpec(no_scope_declared=True,
...)` filing-time shortcut does NOT work yet; use the two-step `new_
ticket` + `set_no_scope_declared` shape until that lands.