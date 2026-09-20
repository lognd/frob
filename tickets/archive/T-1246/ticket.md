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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- docs/design/registry/compliance.yaml
- src/frob/strata/_compliance.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense CCPA re-review narrative into T-1246 body
  actor: logan
  at: '2026-09-19'
  old_length: 868
  new_length: 2096
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
anchor: false
anchor_reason: null
land_commit: null
---
Rows: CMPL-GDPR-CHAPTERS (process, already out_of_scope), CMPL-GDPR-ARTICLES, CMPL-CCPA-CORE-RIGHTS (process, already out_of_scope), CMPL-CPRA-ADDED-RIGHTS (process, already out_of_scope). GDPR already has 3 real RegulationEntry units (ERASURE/RETENTION/BASIS) -- confirm CMPL-GDPR-ARTICLES's handled_by:COMPLIANCE005 is not just riding the disposition-string shape unrelated to those 3. Separately: COMPLIANCE_OUT_OF_SCOPE's CCPA entry justifies out_of_scope via 'PII010 catches it regardless of jurisdiction' -- once T-1242 lands exposure:public-web + a notice/consent RegulationEntry, revisit whether CCPA-CORE-RIGHTS's right-to-know/right-to-delete rights are now partially covered by that new mitigation and whether the out_of_scope reason still holds, or whether it should be split (right-to-know/notice now enforced, right-to-delete still process/out_of_scope).

<!-- narrative-moved:src/frob/strata/_compliance.py:234:T-1246 -->
T-1246 re-review (2026-07-29): T-1242 landed exposure:public-web and
T-1314 landed PRIVACY-NOTICE (mitigation privacy_policy_attestation)
into COMPLIANCE_CATALOG. PRIVACY-NOTICE's notice-at-collection duty
now PARTIALLY discharges CMPL-CCPA-CORE-RIGHTS's right-to-know
component (both are the same "a public collection point must
disclose what it collects" obligation -- PRIVACY-NOTICE's own
RegulationEntry cite already names CCPA Cal. Civ. Code Sec.1798.100
notice-at-collection as a see-also). Right-to-delete has NO
matching coverage: GDPR-ERASURE only fires on a `revocation` edge in
a GDPR jurisdiction, and CCPA carries no separate CA-specific
consumer-deletion-request primitive. This out_of_scope entry is
therefore NOT retired -- it is narrowed and reaffirmed: still
correct for right-to-delete, no longer the whole story for
right-to-know now that PRIVACY-NOTICE exists. Review date extended;
a future ticket may split CCPA-CORE-RIGHTS's disposition into a
real handled_by (right-to-know, via PRIVACY-NOTICE) plus a narrower
out_of_scope (right-to-delete only) once the registry-row-level
split machinery exists to express partial coverage per row.