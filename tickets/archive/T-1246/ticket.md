---
id: T-1246
title: 'compliance triage: GDPR + CCPA/CPRA rows -- classify against real coverage,
  revisit CCPA out_of_scope post exposure:public-web'
state: done
kind: security
origin: human
created: '2026-07-29'
priority: medium
blocked_by:
- T-1242
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
- text: GIVEN this ticket closes WHEN CMPL-GDPR-ARTICLES is inspected THEN its handled_by
    target is confirmed to be a real GDPR-* RegulationEntry set (or a follow-on ticket
    is filed for the gap)
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
- text: GIVEN T-1242 has landed exposure:public-web WHEN COMPLIANCE_OUT_OF_SCOPE's
    CCPA entry is re-read THEN its reason is either reaffirmed with an updated review
    date or replaced by a partial handled_by split, never left silently stale
  evidence:
  - tests/unit/strata/test_compliance.py::TestCmplRegistry::test_check_cmpl_registry_loads_real_file
threat: null
component: null
---
Rows: CMPL-GDPR-CHAPTERS (process, already out_of_scope), CMPL-GDPR-ARTICLES, CMPL-CCPA-CORE-RIGHTS (process, already out_of_scope), CMPL-CPRA-ADDED-RIGHTS (process, already out_of_scope). GDPR already has 3 real RegulationEntry units (ERASURE/RETENTION/BASIS) -- confirm CMPL-GDPR-ARTICLES's handled_by:COMPLIANCE005 is not just riding the disposition-string shape unrelated to those 3. Separately: COMPLIANCE_OUT_OF_SCOPE's CCPA entry justifies out_of_scope via 'PII010 catches it regardless of jurisdiction' -- once T-1242 lands exposure:public-web + a notice/consent RegulationEntry, revisit whether CCPA-CORE-RIGHTS's right-to-know/right-to-delete rights are now partially covered by that new mitigation and whether the out_of_scope reason still holds, or whether it should be split (right-to-know/notice now enforced, right-to-delete still process/out_of_scope).