---
id: T-0189
title: 'catalog: add CWE-611 (XXE) WeaknessEntry to unblock XML external-entity fingerprint'
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
- tests/unit/strata/test_threat.py::TestCwe611Xxe::test_cwe_611_entry_exists_in_the_catalog
- tests/unit/strata/test_threat.py::TestCwe611Xxe::test_cwe_611_is_reachable_via_the_owasp_top_10_view
- tests/unit/strata/test_threat.py::TestCwe611Xxe::test_cwe_611_never_fires_capability_kind_is_none
- tests/unit/strata/test_cve_fingerprint.py::TestXxeFingerprint::test_fp_xxe_parse_001_exists_and_joins_cwe_611
- tests/unit/strata/test_cve_fingerprint.py::TestXxeFingerprint::test_fp_xxe_parse_001_resolves_against_the_default_joined_catalog
- tests/test_vet.py::TestFingerprintScan::test_matches_the_xxe_fingerprint_positive
- tests/test_vet.py::TestFingerprintScan::test_does_not_match_the_xxe_fingerprint_negative
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_catalog_entry_has_a_fixture_mapping
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_unfired_ids_are_exactly_the_capability_kind_none_entries
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-611]
designated_repro_test: null
threat: info-disclosure
component: null
---
T-0153 review follow-up: XXE fingerprint class cut because no CWE-611 WeaknessEntry exists and CVEFP001 refuses fingerprints citing absent CWEs. Add the catalog row, then the fingerprint entry (python lxml etree.parse with resolve_entities, xml.sax without feature_external_ges disabled, java-style patterns out of scope -- only supported languages), litmus positive/negative tests per T-0153's pattern.