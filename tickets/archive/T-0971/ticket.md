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
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/**
- tests/**
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: frob.toml
  reason: PII010/PII012 promotion to error requires editing [gates.severity] in frob.toml
  actor: logan
  at: '2026-07-27'
body_changes:
- mode: append
  reason: 'T-4770: preserve homonym detail trimmed from _keywords.py'
  actor: logan
  at: '2026-09-19'
  old_length: 985
  new_length: 1507
- mode: append
  reason: 'T-4770: preserve DeclarativeBase/Model detail trimmed from _python_fields.py'
  actor: logan
  at: '2026-09-19'
  old_length: 1506
  new_length: 2092
evidence:
- tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_date_of_birth_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_orm_declarative_base_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_django_model_field_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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


T-4770 follow-up (condensed from a T-0971 comment in
src/frob/gates/_pii_structural/_keywords.py, trimmed for DOCARCH002's
12-line cap): the "token" homonyms are a compiled `_*_TOKEN_RE`
provability pattern, a tree-sitter/markdown/CLI-invocation parse token,
a `ContextVar` reset token, or a `uuid4().hex` random directory suffix.
The other homonyms are this repo's own `frob doctor` diagnostic feature
name, PII010's own cross-language gate test names literally testing the
detector, and a plain-English comment word.


T-4770 follow-up (condensed from _STRUCTURE_BASE_NAMES's docstring in
src/frob/gates/_pii_structural/_python_fields.py, trimmed for
DOCARCH002's 12-line cap): this was gates-quality audit finding 14.
`DeclarativeBase` is SQLAlchemy 2.0's own base (class Base(DeclarativeBase)
is the documented idiom so a project's Base is one hop from this name,
not zero); `Model` is Django's models.Model, matched on the bare
Attribute.attr suffix the same way BaseModel/TypedDict already are. The
unresolved third-hop example: class User(OrmBase) where OrmBase itself
subclasses DeclarativeBase.