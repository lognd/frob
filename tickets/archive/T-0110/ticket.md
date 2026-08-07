---
id: T-0110
title: 'threat D: NVD CVE->CWE ingestion into vet + containment report'
state: done
kind: security
origin: human
created: '2026-07-17'
priority: medium
blocked_by:
- T-0113
parent: T-0109
tier: ticket
sprint: null
scope:
- src/frob/vet/**
- src/frob/strata/**
- tests/**
- tickets.md
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_vet_containment.py::TestCveIds::test_cve_advisory_id_is_its_own_cve_id
- tests/test_vet_containment.py::TestCveIds::test_ghsa_advisory_with_cve_alias_resolves
- tests/test_vet_containment.py::TestCveIds::test_ghsa_advisory_with_no_cve_alias_is_honestly_empty
- tests/test_vet_containment.py::TestCveIds::test_dedupes_repeated_cve_ids
- tests/test_vet_containment.py::TestFetchCweForCve::test_fetch_false_with_no_cache_degrades_loudly
- tests/test_vet_containment.py::TestFetchCweForCve::test_network_failure_degrades_loudly
- tests/test_vet_containment.py::TestFetchCweForCve::test_cached_body_parses_cwe_ids
- tests/test_vet_containment.py::TestFetchCweForCve::test_nvd_placeholder_cwe_is_dropped
- tests/test_vet_containment.py::TestFetchCweForCve::test_network_success_populates_cache
- tests/test_vet_containment.py::TestFetchCweForCve::test_malformed_cached_body_degrades_without_raising
- tests/test_vet_containment.py::TestFetchCweForCve::test_expired_cache_entry_triggers_a_fresh_fetch
- tests/test_vet_containment.py::TestFindImportingNodes::test_finds_node_importing_the_package
- tests/test_vet_containment.py::TestFindImportingNodes::test_no_node_imports_the_package
- tests/test_vet_containment.py::TestFindImportingNodes::test_dash_normalized_dist_name_resolves_to_underscore_module
- tests/test_vet_containment.py::TestBuildContainmentReport::test_live_finding_when_obligation_undischarged
- tests/test_vet_containment.py::TestBuildContainmentReport::test_contained_finding_when_obligation_discharged
- tests/test_vet_containment.py::TestBuildContainmentReport::test_unmodeled_when_no_node_imports_the_package
- tests/test_vet_containment.py::TestBuildContainmentReport::test_unverified_when_nvd_lookup_fails
- tests/test_vet_containment.py::TestBuildContainmentReport::test_non_cve_advisory_yields_no_findings
- tests/test_vet_containment.py::TestRenderContainmentReport::test_empty_report_renders_explicit_note
- tests/test_vet_containment.py::TestRenderContainmentReport::test_live_findings_sort_before_contained
- tests/test_vet_containment.py::TestRenderContainmentReport::test_unverified_sorts_between_live_and_contained
designated_repro_test: null
acceptance:
- text: GIVEN a dependency CVE mapping to CWE-89 WHEN the design's CWE-89 obligation
    is discharged THEN vet reports 'contained in depth'; WHEN missing THEN 'live exposure'
    high-severity
  evidence: []
threat: info-disclosure
component: null
---
CVE->CWE join via NVD on top of vet's osv-scanner adapter + cooldown; a vet CVE finding is enriched with its CWE and the design obligation's discharge state; live-exposure severity when the mapped obligation is undischarged. See threat.md phase D.