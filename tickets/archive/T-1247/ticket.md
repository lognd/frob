---
id: T-1247
title: 'compliance triage: NIST 800-53 + NIST-CSF + NIST 800-63 + SSDF rows'
state: done
kind: security
origin: human
created: '2026-07-29'
priority: medium
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
designated_repro_test: null
acceptance:
- text: GIVEN this ticket closes WHEN each of the 3 rows is inspected THEN each carries
    a follow-on ticket reference (for a/b/c) or an explicit out_of_scope reason recorded
    in this ticket's body -- never left as a bare handled_by:COMPLIANCE005
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
threat: null
component: null
---
Rows: CMPL-NIST80053-FAMILIES, CMPL-NISTCSF-FUNCTIONS (process, already out_of_scope), CMPL-NIST80263-VOLUMES, CMPL-SSDF-PRACTICE-GROUPS. All 3 non-out_of_scope rows currently sit at handled_by:COMPLIANCE005 with no corresponding RegulationEntry in COMPLIANCE_CATALOG at all -- classify each: (a) enforceable via existing/extended strata vocabulary + new RegulationEntry, (b) needs new model vocabulary, (c) attestation-only, (d) out of scope with documented reason.