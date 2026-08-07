---
id: T-1250
title: 'compliance triage: CMPL-FROB-CATALOG-ENTRIES row -- the 6 RegulationEntry
  units counted against themselves'
state: done
kind: security
origin: human
created: '2026-07-29'
priority: low
parent: T-1241
tier: ticket
sprint: null
scope:
- docs/design/registry/compliance.yaml
- src/frob/strata/_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
- tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_frob_catalog_entries_self_reference_is_not_flagged
designated_repro_test: null
acceptance:
- text: GIVEN this ticket closes WHEN CMPL-FROB-CATALOG-ENTRIES's disposition comment
    is reviewed THEN it explicitly states it is verified via the 6 real COMPLIANCE_CATALOG
    entries (not merely a non-deferred string), or is corrected if that claim does
    not hold
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
  - tests/unit/strata/test_compliance.py::TestCmplRegistryBacking::test_frob_catalog_entries_self_reference_is_not_flagged
threat: null
component: null
---
CMPL-FROB-CATALOG-ENTRIES (framework frob-std.compliance, leaf_count 6) is the meta-row counting COMPLIANCE_CATALOG's own 6 RegulationEntry units (COPPA, GDPR-ERASURE/RETENTION/BASIS, HIPAA-BAA, MINIMIZATION) as a denominator entry in the registry -- confirm its handled_by:COMPLIANCE005 disposition is not circular (a row about the catalog counted by a gate that only checks the row has a disposition string). Likely fine as-is since the 6 units ARE genuinely implemented with real RegulationEntry+mitigation each, but state that explicitly rather than leaving it riding the same generic handled_by:COMPLIANCE005 text as the 16 other under-enforced rows -- distinguish 'this row is fine because its 6 members are real' from 'this row has a disposition string'.