---
id: T-1249
title: 'compliance triage: OWASP ASVS + SAMM + FedRAMP + SLSA rows'
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
Rows: CMPL-ASVS-CHAPTERS, CMPL-ASVS-REQUIREMENTS, CMPL-ASVS-LEVELS (advisory, already out_of_scope), CMPL-SAMM-FUNCTIONS (process, already out_of_scope), CMPL-SAMM-PRACTICES (process, already out_of_scope), CMPL-FEDRAMP-IMPACT-TIERS, CMPL-SLSA-BUILD-LEVELS. 4 non-out_of_scope rows all sit at handled_by:COMPLIANCE005 with no RegulationEntry backing. ASVS-REQUIREMENTS (286 leaf controls) and SLSA-BUILD-LEVELS are the most plausibly directly enforceable (ASVS overlaps existing security gates, SLSA build-level attestation overlaps supply-chain/provenance tooling if any exists in this repo) -- check for existing overlap with non-compliance gates (e.g. security/PII/secrets families) before proposing new work. Classify each: (a) enforceable via existing/extended vocabulary + new RegulationEntry, (b) needs new model vocabulary, (c) attestation-only, (d) out of scope with documented reason.