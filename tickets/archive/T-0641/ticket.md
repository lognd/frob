---
id: T-0641
title: 'strata: RETRY backoff+jitter + non-idempotent-op guard + IDEMPOTENCY key obligation'
state: done
kind: feature
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0331
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- docs/strata/**
- tests/unit/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_retry.py::TestMissingBackoff::test_retry_flow_without_backoff_fires
- tests/unit/strata/test_retry.py::TestMissingBackoff::test_discharged_and_non_retry_flows_clean
- tests/unit/strata/test_retry.py::TestMissingBackoff::test_waiver_on_one_flow_keeps_sibling_flow_finding
- tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_retry_into_unguarded_dst_fires
- tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_idempotent_dst_discharges
- tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_idempotency_key_dst_discharges
- tests/unit/strata/test_retry.py::TestUnprovenBackoff::test_declared_backoff_with_no_code_evidence_fires
- tests/unit/strata/test_retry.py::TestUnprovenBackoff::test_declared_backoff_with_real_code_evidence_discharges
- tests/unit/strata/test_retry.py::TestUnprovenBackoff::test_declared_backoff_with_no_bound_code_is_uncheckable_not_a_violation
- tests/unit/strata/test_obligation_proof.py::TestOwnerIndex::test_inverts_file_to_node_map
- tests/unit/strata/test_obligation_proof.py::TestNodeHasBoundCode::test_true_when_files_present
- tests/unit/strata/test_obligation_proof.py::TestNodeHasBoundCode::test_false_when_absent
- tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken::test_matches_a_real_token
- tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken::test_no_match_returns_false
- tests/unit/strata/test_obligation_proof.py::TestFilesEvidenceToken::test_unreadable_file_skipped_not_treated_as_proof
- tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_both_endpoints_bound_src_first
- tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_only_dst_bound
- tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_self_loop_deduped
- tests/unit/strata/test_obligation_proof.py::TestBoundEndpoints::test_neither_bound_empty
designated_repro_test: null
acceptance:
- text: Given a flow with retry=true and no backoff/jitter declared, when checked,
    then it fails
  evidence:
  - tests/unit/strata/test_retry.py::TestMissingBackoff::test_retry_flow_without_backoff_fires
- text: Given a retryable flow targeting a non-idempotent mutating op with no idempotency
    key, when checked, then it fails
  evidence:
  - tests/unit/strata/test_retry.py::TestNonIdempotentRetry::test_retry_into_unguarded_dst_fires
threat: null
component: null
---
RETRY flow attr must declare exponential backoff+jitter; a retry on a non-idempotent op is a hard obligation failure unless the target op declares an idempotency key. Proof-against-code: retry loop and backoff params must match declared values; bare declaration insufficient (T-0331 PROVABILITY CONSTRAINT).