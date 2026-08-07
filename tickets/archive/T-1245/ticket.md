---
id: T-1245
title: 'compliance triage: SOC2 + PCI-DSS + HIPAA rows -- classify each against real
  RegulationEntry/attestation coverage'
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
- tests/unit/strata/test_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/unit/strata/test_compliance.py
  reason: 'SELFAUDIT001 fix: docenum001_gate + TestDocenum001Gate need interface declarations
    in design/frob.strata to match the code this ticket added

    '
  actor: logan
  at: '2026-07-29'
evidence:
- tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
designated_repro_test: null
acceptance:
- text: GIVEN this ticket closes WHEN each of the 4 rows is inspected THEN each carries
    one of (a)/(b)/(c)/(d) above, recorded as a follow-on ticket reference or an explicit
    out_of_scope reason in this ticket's body -- never left as a bare handled_by:COMPLIANCE005
    with no further backing
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
threat: null
component: null
---
Rows: CMPL-SOC2-CATEGORIES, CMPL-SOC2-CC-FAMILIES, CMPL-PCIDSS-REQUIREMENTS, CMPL-HIPAA-ADMIN-STANDARDS (process, already out_of_scope), CMPL-HIPAA-PHYSICAL-STANDARDS (advisory, already out_of_scope), CMPL-HIPAA-TECHNICAL-STANDARDS. HIPAA-BAA already has a real RegulationEntry+mitigation (baa_attestation) in COMPLIANCE_CATALOG -- confirm CMPL-HIPAA-TECHNICAL-STANDARDS's handled_by:COMPLIANCE005 is not just a disposition string riding on that unrelated coincidence. For each of the 4 non-out_of_scope rows (SOC2 x2, PCI-DSS, HIPAA-TECHNICAL) classify: (a) enforceable now via existing/extended strata attr vocabulary + new RegulationEntry, (b) needs new model vocabulary, (c) attestation-only (dated artifact + expiry gate, like baa_attestation), (d) genuinely out of scope with a documented reason -- no row left silently riding on the COMPLIANCE005-self-reference shape T-1244 (gate-vacuity child) is closing.