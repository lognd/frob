---
id: T-0971
title: 'Burn-down: PII010/PII012 to zero unwaived, then promote to ERROR (167 findings)'
state: done
kind: security
origin: auditor
created: '2026-07-27'
priority: medium
parent: T-0969
tier: ticket
sprint: null
scope:
- src/**
- tests/**
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: PII010/PII012 promotion to error requires editing [gates.severity] in frob.toml
  actor: logan
  at: '2026-07-27'
evidence:
- tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_date_of_birth_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_orm_declarative_base_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_django_model_field_fires
designated_repro_test: null
threat: null
component: null
---
gates-quality audit (T-0399) finding 4/5: PII010/PII012 are WARN and
never block `frob check`. Live measured count on main (chunked
`gates-security`, 2026-07-27): 167 unwaived PII010/PII012 warnings (3
already carry a reasoned frob:waive). Owner-gate: PII010 in
[gates.severity] (PII012 has no entry today -- add one alongside).

Plan: triage the 167 findings -- real PII-shaped fields get a std.pii
`carries` tag or get renamed/typed away from the trigger; genuine
false positives (raw /etc/passwd audit diffs, keyword-sweep hits like
'token'/'diagnosis' that are not credentials/health data) get a reasoned
`frob:waive PII01# reason="..."`. Also close audit finding 5 (camelCase
field-name blindness in `_field_name_hit`) and finding 14 (ORM-base
blindness in `_is_data_structure`) as part of this pass so the promoted
gate does not immediately need a re-audit for coverage gaps. Once the
unwaived count is at or near zero, flip [gates.severity] PII010/PII012 =
"error" in frob.toml.