---
id: T-1241
title: 'compliance: enforce the 27-row corpus, not catalogue it'
state: done
kind: security
origin: human
created: '2026-07-29'
priority: high
parent: null
tier: epic
sprint: null
scope:
- docs/design/registry/compliance.yaml
- src/frob/strata/_compliance.py
- src/frob/gates/_decisions_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_public_web_node_with_no_mitigation_refutes
- tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_declared_privacy_policy_attr_discharges
- tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_owner_and_review_override_clears_privacy_notice
designated_repro_test: null
acceptance:
- text: GIVEN this epic's children all close WHEN a fresh reader asks 'is CCPA/GDPR
    notice enforced' THEN the answer is a named RegulationEntry+mitigation+test+gate,
    not a disposition string
  evidence:
  - tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_public_web_node_with_no_mitigation_refutes
  - tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_declared_privacy_policy_attr_discharges
  - tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_owner_and_review_override_clears_privacy_notice
threat: null
component: null
---
User directive 2026-07-29: compliance coverage must be ENFORCED, not catalogued. Standing repo principle: a registry row read by zero code is orphaned docs presented as implemented; a completion claim needs a passing gate. State as of filing: 27 CMPL-* rows in docs/design/registry/compliance.yaml are all unit-level dispositioned (10 out_of_scope process/advisory, 17 handled_by:COMPLIANCE005), but COMPLIANCE005 only checks that a disposition STRING exists -- it does not verify any real mitigation predicate or model vocabulary backs the 17 handled_by units. Only 6 RegulationEntry/mitigation pairs exist in COMPLIANCE_CATALOG (COPPA, GDPR-ERASURE/RETENTION/BASIS, HIPAA-BAA, MINIMIZATION). No exposure:public-web (or equivalent) attr vocabulary exists, so nothing today forces a public web-facing node to carry a privacy-policy/notice/consent mitigation -- the user's concrete example of catalogued-not-enforced. CCPA/CPRA sit as OutOfScopeRegulation entries (caught_by PII010) -- worth revisiting once exposure:public-web lands, not force-closed here.