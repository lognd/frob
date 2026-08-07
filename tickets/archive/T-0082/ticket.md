---
id: T-0082
title: 'strata std.secrets: credentials as cache-of-authority'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0053
parent: T-0054
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_issue_flow_carries_lifetime_as_age
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_revocation_edge_is_mandatory
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_revocation_edge_present_when_declared
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_unknown_issuer_fails_closed
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_unknown_audience_member_fails_closed
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_lifetime_wrong_dimension_fails_closed
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_revoke_wrong_dimension_fails_closed
- tests/unit/strata/test_secrets.py::TestSecretElaboration::test_auto_generated_readers_claim
- tests/unit/strata/test_secrets.py::TestAgePropagationReuse::test_lifetime_joins_existing_age_bound_claim
- tests/unit/strata/test_secrets.py::TestReadersExactSetClosure::test_readers_claim_proved_on_exact_match
- tests/unit/strata/test_secrets.py::TestReadersExactSetClosure::test_readers_claim_refutes_on_extra_reader
- tests/unit/strata/test_secrets.py::TestReadersExactSetClosure::test_readers_claim_refutes_on_missing_reader
- tests/unit/strata/test_secrets.py::TestSecretLabelViolations::test_secret_resting_at_public_clearance_node_is_flagged
- tests/unit/strata/test_secrets.py::TestSecretLabelViolations::test_secret_resting_at_secret_clearance_node_is_not_flagged
- tests/unit/strata/test_secrets.py::TestRevocationReachability::test_revocation_edge_is_a_real_reach_claim_target
- tests/unit/strata/test_secrets.py::TestReadersExactSetClosure::test_readers_claim_refutes_across_a_declassify_boundary
designated_repro_test: null
threat: info-disclosure
component: null
---
issued-by/audience/lifetime/revocation; no credential without a revocation edge (same rule as cache invalidation); readers() as exact-set closure; secret-in-logs/repo/artifact become label violations.