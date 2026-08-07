---
id: T-1020
title: 'REG008 burn-down: 132 handled_by dispositions lack the frob:enforces edge
  in code'
state: done
kind: bug
origin: human
created: '2026-07-27'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- docs/design/registry/arch-checks.yaml
- src/frob/arch/
- src/frob/dup/_rules.py
- tests/test_registry_exhaustiveness.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/dup/_rules.py
  reason: 'T-1020: DUP001''s real enforcing site (frob.dup._rules.DUP001) lives outside
    src/frob/arch/ -- widening scope to add the two missing frob:enforces edges (ACC-1-5-DRY,
    ACC-4-COPY-PASTE), verified DUP001 already carries the analogous ACC-2-1-DUPLICATED-CODE
    edge as precedent'
  actor: logan
  at: '2026-07-27'
- op: add
  glob: tests/test_registry_exhaustiveness.py
  reason: 'T-1020: add a real-repo-scan regression test proving zero REG008 findings
    for docs/design/registry/arch-checks.yaml, the acceptance criterion''s own proof
    surface'
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_registry_exhaustiveness.py::TestArchChecksReg008BurnDown::test_no_reg008_findings_for_arch_checks_yaml
- tests/unit/test_arch_srp.py::TestLcom4::test_disjoint_field_groups_trigger_lcom4
- tests/unit/test_arch_srp.py::TestLcom4::test_shared_fields_do_not_trigger_lcom4
designated_repro_test: null
acceptance:
- text: GIVEN a full frob check run THEN REG008 warnings are zero
  evidence:
  - tests/test_registry_exhaustiveness.py::TestArchChecksReg008BurnDown::test_no_reg008_findings_for_arch_checks_yaml
threat: null
component: null
---
REG008: registry entries dispositioned handled_by:<RULE> need a matching frob:enforces <ENTRY-ID> directive on the enforcing rule implementation. Add the 132 missing edges at the real enforcing sites (no bulk misattribution: verify each rule actually covers the entry before adding the edge; downgrade the disposition honestly where it does not).