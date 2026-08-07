---
id: T-1242
title: 'compliance: exposure:public-web attr + PRIVACY-NOTICE RegulationEntry -- public
  web-facing nodes demand a privacy-policy mitigation'
state: done
kind: feature
origin: human
created: '2026-07-29'
priority: high
parent: T-1241
tier: ticket
sprint: null
scope:
- src/frob/strata/_compliance.py
- src/frob/strata/_models.py
- docs/strata/threat.md
- docs/guides/extending/compliance-registry.md
- tests/unit/strata/test_compliance.py
- docs/design/compliance-corpus.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_compliance.py
  reason: PRIVACY-NOTICE tests + corpus enumeration table both need touching per T-1242's
    own instructions
  actor: logan
  at: '2026-07-29'
- op: add
  glob: docs/design/compliance-corpus.md
  reason: PRIVACY-NOTICE tests + corpus enumeration table both need touching per T-1242's
    own instructions
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_public_web_node_with_no_mitigation_refutes
- tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_declared_privacy_policy_attr_discharges
- tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_no_public_web_exposure_is_silent
designated_repro_test: null
acceptance:
- text: GIVEN a strata model with a public web-facing Node (exposure:public-web) handling
    Pii-or-above data and no privacy-policy mitigation and no Claim override WHEN
    evaluate_compliance runs THEN it emits a COMPLIANCE00x violation and the compliance
    gate fails
  evidence:
  - tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_public_web_node_with_no_mitigation_refutes
- text: GIVEN the same model but with a declared privacy-policy mitigation (or an
    owner+review Claim override) WHEN evaluate_compliance runs THEN no violation fires
  evidence:
  - tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_declared_privacy_policy_attr_discharges
- text: GIVEN a model with no exposure:public-web node at all WHEN evaluate_compliance
    runs THEN the check is silent (not vacuously firing on unrelated models)
  evidence:
  - tests/unit/strata/test_compliance.py::TestPrivacyNotice::test_no_public_web_exposure_is_silent
threat: null
component: null
---
User's concrete example, buildable now without waiting on the framework-family triage children (T-1241's other children just classify rows; this introduces the one new piece of model vocabulary several of them will point at). Add exposure:public-web as a new Node attr prefix (same opaque-string attrs convention as subject:/jurisdiction:/basis:, module docstring's 'no new kernel primitive' law). Add a RegulationEntry (id e.g. PRIVACY-NOTICE) with a mitigation predicate: a public-web-exposed Node handling Pii-or-above data must have an associated privacy-policy/notice mitigation (reuse the existing PrivacyPolicy/check_privacy_policy (COMPLIANCE003) machinery as the notice-existence proof, or a new structural check colocated in _compliance.py) or an explicit Claim override with owner+review (module docstring's assume-override convention). Wire into REGULATION_VIEWS (a ccpa/notice view) and COMPLIANCE_CATALOG.