---
id: T-0145
title: 'per-CWE litmus fixtures: every catalog weakness fires from real .strata source'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/strata/litmus/**
- tests/unit/strata/test_litmus_cwe.py
- docs/strata/threat.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_catalog_entry_has_a_fixture_mapping
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_unfired_ids_are_exactly_the_capability_kind_none_entries
- tests/unit/strata/test_litmus_cwe.py::TestFixtureCoverageIsExhaustive::test_every_firing_id_also_has_a_hardened_fixture
- tests/unit/strata/test_litmus_cwe.py::TestOutOfScopeExemptionMatchesCatalogExactly::test_cwe_top_25_view_is_satisfied_by_the_litmus_catalog
- tests/unit/strata/test_litmus_cwe.py::TestOutOfScopeExemptionMatchesCatalogExactly::test_out_of_scope_ids_are_disjoint_from_the_fixture_catalog
- tests/unit/strata/test_litmus_cwe.py::TestOutOfScopeExemptionMatchesCatalogExactly::test_out_of_scope_ids_cover_the_top_25_gap_exactly
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-502]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-78]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-79]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-89]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-918]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-922]
- tests/unit/strata/test_litmus_cwe.py::TestFiringFromParsedSurfaceSource::test_fires_undischarged[CWE-94]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-502]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-78]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-79]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-89]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-918]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-922]
- tests/unit/strata/test_litmus_cwe.py::TestHardenedDischargesFromParsedSurfaceSource::test_discharges_cleanly[CWE-94]
- tests/unit/strata/test_litmus_cwe.py::TestSharedExecCapabilityDischargesIndependently::test_vuln_fixture_fires_both_independently
- tests/unit/strata/test_litmus_cwe.py::TestSharedExecCapabilityDischargesIndependently::test_hardened_fixture_discharges_both_independently
- tests/unit/strata/test_litmus_cwe.py::TestSharedExecCapabilityDischargesIndependently::test_discharging_only_one_leaves_the_other_undischarged
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-22]
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-352]
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_never_fires_even_in_a_plausible_vulnerable_scenario[CWE-798]
- tests/unit/strata/test_litmus_cwe.py::TestCapabilityKindNoneEntriesNeverFireByDesign::test_capability_kind_is_none_for_all_three
designated_repro_test: null
threat: null
component: null
---
Every WeaknessEntry in CWE_CATALOG and CWE_TOP_25_CATALOG must be exercised by a real .strata litmus project in which its obligation FIRES from parsed surface source (strata_core parse of a .strata file), not from hand-built kernel objects -- plus a hardened variant that discharges it wherever the kernel can express the mitigation. Parametrize the test over the union of both catalogs so adding a WeaknessEntry without a firing fixture FAILS the suite (vacuous-pass doctrine, drift-lock style like the tmLanguage keyword parity test). Follow the existing vuln/hardened litmus pair precedent. OutOfScopeEntry rows are exempt but the test must assert the exemption list matches the catalog's out-of-scope ids exactly so nothing silently escapes.