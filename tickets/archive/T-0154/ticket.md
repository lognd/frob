---
id: T-0154
title: 'PII declarations: first-class personal-data modeling and flow proofs in strata'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/**
- src/frob/strata/**
- design/frob.strata
- tests/unit/strata/**
- docs/strata/**
- tickets.md
- editors/vscode-strata/syntaxes/strata.tmLanguage.json
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_pii.py::TestPiiTagHelpers::test_node_pii_tags_reads_pii_prefixed_attrs
- tests/unit/strata/test_pii.py::TestPiiCatalog::test_unknown_category_is_pii001
- tests/unit/strata/test_pii.py::TestPiiBoundaryProtection::test_crossing_trust_into_pii_store_fires_pii002
- tests/unit/strata/test_pii.py::TestPiiBoundaryProtection::test_assumed_claim_with_owner_and_review_discharges
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_pii_with_no_retention_or_erasure_fires_pii003
- tests/unit/strata/test_pii.py::TestPiiRetentionErasure::test_revocation_edge_discharges
- tests/unit/strata/test_pii.py::TestPiiUndeclaredFlow::test_underlabeled_flow_fires_pii004
- tests/unit/strata/test_pii.py::TestEvaluatePii::test_joins_every_check
- tests/unit/strata/test_pii.py::TestFrobSelfModelPiiPosture::test_frob_design_declares_zero_pii
- tests/unit/strata/test_pii.py::TestFrobSelfModelPiiPosture::test_frob_design_pii_audit_is_clean
- tests/unit/strata/test_litmus_pii.py::TestPiiVulnLitmus::test_vuln_fires_boundary_retention_and_lint
- tests/unit/strata/test_litmus_pii.py::TestPiiHardenedLitmus::test_hardened_discharges_every_fired_obligation
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_pii_gap_reported
- tests/unit/test_strata_tmlanguage.py::test_clause_keywords_covered_by_grammar
designated_repro_test: null
threat: null
component: null
---
Scope note: `editors/vscode-strata/syntaxes/strata.tmLanguage.json` added
to scope after landing -- the new `carries` clause keyword in
`strata-core/src/parse.rs` trips `tests/unit/test_strata_tmlanguage.py::
test_clause_keywords_covered_by_grammar`'s bidirectional drift-lock (a
parser keyword with no tmLanguage highlight entry fails the suite), so
adding `carries` to the grammar's `clause-keywords` pattern is a required
consequence of this ticket's own grammar change, not a neighboring
improvement -- same class of cascading consequence T-0150/T-0151 already
established as in-scope-by-necessity.

First-class PII in the design language. INVESTIGATE FIRST: the compliance layer (COPPA/GDPR/HIPAA views), kernel Flow/Boundary/Claim machinery, and the T-0132 code/may attr grammar -- reuse, never parallel-build (T-0150 round-1 lesson). Feature: declare what personal data a node/store/flow carries (e.g. carries "pii.email", categories: identifier, contact, financial, health, biometric, behavioral, credentials) in surface grammar + elaboration + kernel; prover joins: PII crossing a trust boundary without a declared protection (encryption/pseudonymization/consent) is a violation; stores carrying PII require declared retention and erasure paths feeding the GDPR/HIPAA views (join to existing compliance obligations rather than duplicating them); undeclared-PII linting where flows source from stores with declared PII. Litmus vuln/hardened pair firing and discharging each new rule from parsed surface source. Self-model: declare frob's own PII posture in design/frob.strata (expected: none beyond git author metadata -- proving the zero case counts and must be explicit, not silent). Seccomp/self-model goldens regenerated if affected, per T-0150 precedent.