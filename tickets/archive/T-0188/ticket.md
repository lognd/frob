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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/**
- tests/**
- docs/strata/threat.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense CWE-295 placement rationale into T-0188 body
  actor: logan
  at: '2026-09-19'
  old_length: 638
  new_length: 2131
evidence:
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_cwe_295_is_cataloged_with_no_capability_kind_or_view
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_matches_tls_verify_false_python
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_no_match_on_verified_tls_python
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_matches_tls_reject_unauthorized_false_node
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_no_match_on_reject_unauthorized_true_node
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_matches_tls_danger_accept_invalid_certs_rust
- tests/vet_suite/test_fingerprint.py::TestFingerprintScan::test_no_match_on_default_reqwest_builder_rust
designated_repro_test: null
threat: spoofing
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-0153 review follow-up: the TLS verify=False fingerprint class was correctly cut because no CWE-295 WeaknessEntry exists in CWE_CATALOG/CWE_TOP_25_CATALOG/QUALITY_CATALOG and the CVEFP001 drift-lock (rightly) refuses fingerprints citing absent CWEs. Add the catalog row (with honest views placement), then the fingerprint entry (requests/httpx/aiohttp verify=False, node tls rejectUnauthorized false, rust danger_accept_invalid_certs), litmus positive/negative source tests per T-0153's pattern. Also reconcile CWE-916 (mentioned in _cve_fingerprint.py docstring but in neither catalog nor cut-class list) -- add it or fix the docstring.

<!-- narrative-moved:src/frob/strata/_threat_catalog_quality.py:79:T-0188 -->
T-0188 (docs/strata/threat.md#cve-fingerprints-code-level-pattern-
catalog-t-0153, "curated, not exhaustive"): honest views
placement -- neither `CWE_CATALOG` (the verified 8-id `owasp-
top-10` transcription) nor `CWE_TOP_25_CATALOG` (the verified
2023 MITRE Top 25 membership, `_CWE_TOP_25_IDS` above -- CWE-295
is NOT one of the 25) claims this id without a fresh, dated
re-verification against those specific pinned lists; adding it
there would silently widen a view whose membership this module's
own docstrings describe as independently checked. Cataloged here
in `QUALITY_CATALOG` instead (already home to other
`family="security"` rows, e.g. CWE-639 above) with NO `QUALITY_
VIEWS` membership -- mirrors CWE-639/REL-001's own precedent of a
catalog entry that need not belong to any named baseline view
(`check_catalog_completeness` is per-view, not "every entry must
have a view", `TestQualityFamilies` in test_threat.py). No
`capability_kind`: TLS certificate-verification bypass (`verify=
False` and its cross-language siblings) is not a `may`-capability
auto-instantiation shape (`_effects.py::_may_kind` has no
tls-verification kind) -- it is fired exclusively by the
`std.cve` fingerprint layer (`_cve_fingerprint.py`'s
FP-TLS-VERIFY-* entries) matching the literal disable-verification
needle, the SAME "citation-only, discharge lives elsewhere"
shape CWE-798/352 already use in `CWE_CATALOG` above.