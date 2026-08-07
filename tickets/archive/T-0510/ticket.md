---
id: T-0510
title: add missing CWE-916/1321/1333/601/1336 WeaknessEntry rows and cve-fingerprint
  needles
state: done
kind: feature
origin: human
created: '2026-07-21'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/strata/_cve_fingerprint.py
- src/frob/strata/_threat.py
- docs/design/security-corpus.md
- docs/design/registry/weaknesses.yaml
- .frob-release.json
- CHANGELOG.md
- pyproject.toml
- uv.lock
- tests/unit/strata/test_cve_fingerprint.py
- tests/unit/strata/test_threat.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/design/registry/weaknesses.yaml
  reason: ticket body explicitly requires flipping the 5 CWE-916/1321/1333/601/1336
    dispositions from deferred:T-0510 to handled_by once the fingerprints ship
  actor: logan
  at: '2026-07-21'
- op: add
  glob: .frob-release.json
  reason: REL001 public-API bump for this ticket's new WeaknessEntry/CveFingerprint
    additions requires version/changelog/lock/release-stamp files
  actor: logan
  at: '2026-07-21'
- op: add
  glob: CHANGELOG.md
  reason: REL001 public-API bump for this ticket's new WeaknessEntry/CveFingerprint
    additions requires version/changelog/lock/release-stamp files
  actor: logan
  at: '2026-07-21'
- op: add
  glob: pyproject.toml
  reason: REL001 public-API bump for this ticket's new WeaknessEntry/CveFingerprint
    additions requires version/changelog/lock/release-stamp files
  actor: logan
  at: '2026-07-21'
- op: add
  glob: uv.lock
  reason: REL001 public-API bump for this ticket's new WeaknessEntry/CveFingerprint
    additions requires version/changelog/lock/release-stamp files
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_cve_fingerprint.py
  reason: counterexample-first evidence tests added for the 5 new fingerprints/WeaknessEntry
    rows
  actor: logan
  at: '2026-07-21'
- op: add
  glob: tests/unit/strata/test_threat.py
  reason: counterexample-first evidence tests added for the 5 new fingerprints/WeaknessEntry
    rows
  actor: logan
  at: '2026-07-21'
evidence:
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-WEAKHASH-PASSWORD-001]
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-PROTO-POLLUTION-001]
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-REDOS-REGEX-001]
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-OPEN-REDIRECT-001]
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_entry_exists_and_joins_expected_cwe[FP-SSTI-TEMPLATE-001]
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_all_five_resolve_against_the_default_joined_catalog
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_weakhash_needle_fires_on_smelly_python
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_weakhash_needle_does_not_fire_on_clean_python
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_proto_pollution_needle_fires_on_smelly_typescript
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_redos_needle_fires_on_smelly_typescript
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_open_redirect_needle_fires_on_smelly_python
- tests/unit/strata/test_cve_fingerprint.py::TestT0510Fingerprints::test_ssti_needle_fires_on_smelly_python
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-916]
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-1321]
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-1333]
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-601]
- tests/unit/strata/test_threat.py::TestQualityFamilies::test_t0510_entries_are_cataloged_with_no_capability_kind_or_view[CWE-1336]
designated_repro_test: null
threat: null
component: null
---
Found while working T-0508. weaknesses.yaml carries 5 SEC-CVE-FINGERPRINT-CWE-* entries (CWE-916-WEAK-HASH, CWE-1321-PROTO-POLLUTION, CWE-1333-REDOS, CWE-601-OPEN-REDIRECT, CWE-1336-SSTI) with checkability=advisory but NO shipped CveFingerprint needle exists for any of them in _cve_fingerprint.py's CVE_FINGERPRINTS catalog, and no WeaknessEntry row exists in any of CWE_CATALOG/CWE_TOP_25_CATALOG/QUALITY_CATALOG (_threat.py) for these CWE ids either (confirmed: the only CWE-916/601/1321/1333/1336 rows in weaknesses.yaml are CWE-1000-registry rows, source_doc=docs/design/cwe-1000-registry.md, disposition=out-of-scope, a different framework than cve-fingerprint) -- so check_fingerprint_catalog_drift (CVEFP001) would correctly reject a fingerprint naming any of these cwe_id today. _cve_fingerprint.py's own module docstring already discloses the CWE-916 half of this gap and names it as needing a follow-up ticket adding the missing WeaknessEntry row before a fingerprint can honestly join it. This ticket: add the missing WeaknessEntry rows (or route through an existing one if a real match is found on closer research) plus a real, independently-verified CVE-cited needle per CWE, in a scanned language (python/typescript/rust/c-cpp), following the same pattern FP-TLS-VERIFY-*/FP-XXE-PARSE-* used for the CWE-295/CWE-611 disclosed-gap precedent.