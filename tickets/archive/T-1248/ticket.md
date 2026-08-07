---
id: T-1248
title: 'compliance triage: ISO 27002 themes/controls + CIS controls/safeguards/implementation-groups
  rows'
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
- text: GIVEN this ticket closes WHEN each of the 4 rows is inspected THEN each carries
    a follow-on ticket reference (for a/b/c) or an explicit out_of_scope reason recorded
    in this ticket's body -- never left as a bare handled_by:COMPLIANCE005
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
threat: null
component: null
---
Rows: CMPL-ISO27002-THEMES, CMPL-ISO27002-CONTROLS, CMPL-CIS-CONTROLS, CMPL-CIS-SAFEGUARDS, CMPL-CIS-IMPLEMENTATION-GROUPS (advisory, already out_of_scope). The 4 non-out_of_scope rows all sit at handled_by:COMPLIANCE005 with no RegulationEntry backing. CIS-SAFEGUARDS alone is 153 leaf controls (config-checkability) -- do not attempt per-leaf enforcement here, classify at the unit/family level: (a) enforceable via existing/extended vocabulary + new RegulationEntry(ies), (b) needs new model vocabulary, (c) attestation-only, (d) out of scope with documented reason.