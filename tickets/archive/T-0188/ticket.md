---
id: T-0188
title: 'catalog: add CWE-295 (improper cert validation) WeaknessEntry to unblock TLS
  verify=False fingerprint'
state: done
kind: security
origin: agent
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_cwe_295_is_cataloged_with_no_capability_kind_or_view
- tests/test_vet.py::TestFingerprintScan::test_matches_tls_verify_false_python
- tests/test_vet.py::TestFingerprintScan::test_no_match_on_verified_tls_python
- tests/test_vet.py::TestFingerprintScan::test_matches_tls_reject_unauthorized_false_node
- tests/test_vet.py::TestFingerprintScan::test_no_match_on_reject_unauthorized_true_node
- tests/test_vet.py::TestFingerprintScan::test_matches_tls_danger_accept_invalid_certs_rust
- tests/test_vet.py::TestFingerprintScan::test_no_match_on_default_reqwest_builder_rust
designated_repro_test: null
threat: spoofing
component: null
---
T-0153 review follow-up: the TLS verify=False fingerprint class was correctly cut because no CWE-295 WeaknessEntry exists in CWE_CATALOG/CWE_TOP_25_CATALOG/QUALITY_CATALOG and the CVEFP001 drift-lock (rightly) refuses fingerprints citing absent CWEs. Add the catalog row (with honest views placement), then the fingerprint entry (requests/httpx/aiohttp verify=False, node tls rejectUnauthorized false, rust danger_accept_invalid_certs), litmus positive/negative source tests per T-0153's pattern. Also reconcile CWE-916 (mentioned in _cve_fingerprint.py docstring but in neither catalog nor cut-class list) -- add it or fix the docstring.