---
id: T-3934
title: 'CI red: T-3787 target_branch kwarg breaks 6 land-proof tests on all platforms'
state: done
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_ticket_land_proof_claims.py
scope_breadth_ack: true
scope_breadth_ack_reason: SCOPE002 flags pre-existing frob:tests directives in src/frob/tickets/_land.py
  (added at T-2091/T-2255, predating this ticket) pointing at two of this file's test
  names; this ticket's fix only updates test doubles to accept the target_branch kwarg
  and does not touch _land.py's production code, so its scope stays narrowly the test
  file per the briefing's explicit STOP-and-report rule rather than widening scope
  on my own
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_skipped_unmeasured_is_not_printed_as_verified_true
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_passed_healthy_path_is_unchanged
- tests/test_ticket_land_proof_claims.py::TestLandProofClaimsOutcome::test_no_recorded_outcome_leaves_verified_unaffected
- tests/test_ticket_land_proof_claims.py::TestLandProofOrphanEvidenceOutcome::test_skipped_unmeasured_is_surfaced_not_dropped
- tests/test_ticket_land_proof_claims.py::TestLandProofOrphanEvidenceOutcome::test_ran_healthy_path_is_printed
- tests/test_ticket_land_proof_claims.py::TestLandProofOrphanEvidenceOutcome::test_no_recorded_outcome_prints_unknown
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Run 34005559354 (28a511c9f) fails on ubuntu, macOS AND windows with 6 identical failures:

TypeError: <lambda>() got an unexpected keyword argument 'target_branch'

in tests/test_ticket_land_proof_claims.py -- TestLandProofClaimsOutcome and TestLandProofOrphanEvidenceOutcome. Commit 68fe479f7 (land T-3787, non-main target branch) added a target_branch kwarg to the landing call site; the test doubles are lambdas with the old signature, so every one raises on call.

This is a landed regression from our own most recent commit and is the single largest shared cause of red across all three platforms.

FIX: update the test doubles to accept target_branch. Do NOT change production code to restore the old signature -- T-3787's kwarg is intended. Assert the doubles receive the value they should rather than swallowing it with a bare catch-all, so the test still constrains the call.

ACCEPTANCE: the 6 named tests pass locally; no other test in the file regresses.