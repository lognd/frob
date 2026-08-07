---
id: T-0153
title: 'std.cve fingerprints: pattern catalog for known vulnerable-usage classes'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0158
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/**
- src/frob/vet/_capability.py
- src/frob/vet/_scan.py
- tests/unit/strata/**
- tests/test_vet.py
- docs/strata/threat.md
- docs/modules/vet.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_every_fingerprint_has_at_least_one_cve_citation
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_every_fingerprint_has_at_least_one_needle
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_every_fingerprint_language_is_a_scanned_bucket
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_fingerprint_ids_are_unique
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogShape::test_view_membership_matches_the_catalog_exactly
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_default_catalog_is_drift_clean
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_every_fingerprint_cwe_id_resolves_against_the_joined_catalog
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_unknown_cwe_id_fails_loudly
- tests/unit/strata/test_cve_fingerprint.py::TestCatalogDrift::test_a_removed_cwe_entry_is_detected_against_a_narrowed_catalog
- tests/test_vet.py::TestFingerprintScan::test_matches_a_known_fingerprint
- tests/test_vet.py::TestFingerprintScan::test_no_match_on_clean_source
- tests/test_vet.py::TestFingerprintScan::test_no_language_returns_empty
- tests/test_vet.py::TestFingerprintScan::test_unreadable_file_returns_empty
- tests/test_vet.py::TestFingerprintScan::test_language_mismatch_does_not_match
- tests/test_vet.py::TestFingerprintScan::test_own_catalog_file_excluded_from_directory_aggregation
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_aggregates_across_files
- tests/test_vet.py::TestFingerprintScan::test_scan_directory_fingerprints_excludes_the_catalog_itself
- tests/test_vet.py::TestScanTreeWithLocalSource::test_scan_tree_surfaces_a_cve_fingerprint_finding
- tests/unit/strata/test_audit.py::TestExhaustiveness::test_cve_fingerprint_catalog_checked_every_call
designated_repro_test: null
threat: null
component: null
---
Extend the standard library beyond CWE entries with CVE FINGERPRINTS: code-level patterns for canonical vulnerable-usage classes, so the scanner can flag the pattern in our own code and in vetted dependency source -- not just match dependency versions against the mirror (T-0146/T-0147 handle that). Model: CveFingerprint entries (id, title, cve cite(s), linked cwe id joining the existing catalogs, language, detection needles following vet _capability's recall-over-precision substring philosophy including the T-0151 dot-exclusion lessons, remediation guidance). Curated starter set of 10-15 canonical classes with REAL citations, e.g.: pickle.loads on untrusted data, yaml.load without SafeLoader, subprocess shell=True with interpolation, requests verify=False, weak-hash password storage, jndi-style lookup injection (Log4Shell class), eval on request data, tarfile extractall path traversal, xml external entities. Each fingerprint drift-locked to the CWE catalog (unknown cwe id fails loudly) and exercised by fire/discharge fixtures in the litmus style. Wire into vet scan output and into the threat catalog views as a separate table following the CWE_TOP_25_VIEWS precedent (do not silently widen default views). Honest limits documented: substring fingerprints have false-positive classes -- document them per T-0151's precedent rather than half-building AST precision.