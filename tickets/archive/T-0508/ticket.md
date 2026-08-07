---
id: T-0508
title: reconcile weaknesses.yaml SEC-CVE-FINGERPRINT-* dispositions now that T-0439
  shipped SEC-CVE-FINGERPRINT-001
state: done
kind: bug
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- docs/design/registry/weaknesses.yaml
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'bind evidence: the only test suite that exercises weaknesses.yaml disposition
    validity (D-02 evidence-scope binding requires an evidence file/TESTS-edge inside
    declared scope; weaknesses.yaml is pure data with no coverable code symbol of
    its own)'
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_registry_exhaustiveness.py::TestDisposition::test_handled_by_real_rule_passes
- tests/test_registry_exhaustiveness.py::TestDisposition::test_deferred_to_open_ticket_passes
- tests/unit/strata/test_cve_fingerprint_scan.py::TestGate::test_smelly_file_fires
- tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints::test_real_catalog_pickle_needle_fires
- tests/unit/strata/test_cve_fingerprint.py::TestXxeFingerprint::test_fp_xxe_parse_001_exists_and_joins_cwe_611
designated_repro_test: null
threat: null
component: null
---
Found while working T-0496/checking frob check output after closing T-0439. docs/design/registry/weaknesses.yaml carries 16 SEC-CVE-FINGERPRINT-* entries (lines ~6717-6827) with disposition: deferred:T-0439, anticipating exactly the gate T-0439 shipped (SEC-CVE-FINGERPRINT-001, src/frob/gates/_cve_fingerprint_scan.py). Now that T-0439 is done, REG003 fires on all 16 (deferral to a closed ticket is not a real deferral). This was a real oversight in T-0439's own scope (docs/design/registry/weaknesses.yaml was already in T-0439's declared scope from the start) -- T-0439's Done report incorrectly claimed nothing needed updating there. Reconciliation is NOT a blind find-and-replace: 9 entries are checkability=needle-detectable with an id matching a real shipped CVE_FINGERPRINTS entry (FP-EXEC-SHELL-001, FP-XSS-JQUERY-001, FP-PATH-TAR-001, FP-DESERIALIZE-YAML-001, FP-DESERIALIZE-PICKLE-001, FP-SQLI-STRFMT-001, FP-SSRF-FETCH-001, FP-CODEEVAL-TEMPLATE-001, FP-HARDCODED-CRED-001) -- these should become handled_by:SEC-CVE-FINGERPRINT-001. The other 7 are checkability=advisory (CWE-295-TLS-VERIFY, CWE-916-WEAK-HASH, CWE-611-XXE, CWE-1321-PROTO-POLLUTION, CWE-1333-REDOS, CWE-601-OPEN-REDIRECT, CWE-1336-SSTI) and do NOT map 1:1 to the shipped catalog: CWE-916 is explicitly still out-of-scope per _cve_fingerprint.py's own docstring (no WeaknessEntry exists for it yet); CWE-611/CWE-295 ARE shipped but under different fingerprint ids (FP-XXE-PARSE-001, FP-TLS-VERIFY-001/002/003) than the registry's generic CWE-*-named rows, needing a cross_refs join or a renamed id, not a bare handled_by; CWE-1321/1333/601/1336 have no shipped fingerprint at all. Needs a careful per-entry pass, not a mechanical sweep.