---
id: T-0348
title: 'structural PII/secrets: DB/DDL schema scanning (family 2)'
state: done
kind: feature
origin: human
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- tests/test_gates.py
- docs/modules/gates.md
- tests/test_pii_structural_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_gates.py
  reason: T-0348 gates work maps to tests/test_gates.py
  actor: logan
  at: '2026-07-20'
- op: remove
  glob: docs/**
  reason: 'scope hygiene (T-0455): narrow speculative docs/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: docs/modules/gates.md
  reason: T-0348 gates work maps to docs/modules/gates.md
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_pii_structural_gate.py
  reason: T-0455 scope hygiene narrowed tests/** to tests/test_gates.py, the wrong
    mirrored path -- this family's actual test file (used as T-0207 predecessor's
    evidence) is tests/test_pii_structural_gate.py
  actor: logan
  at: '2026-07-21'
evidence:
- tests/test_pii_structural_gate.py::TestDdlSchema::test_orm_column_password_fires
- tests/test_pii_structural_gate.py::TestDdlSchema::test_alembic_positional_column_ssn_fires
- tests/test_pii_structural_gate.py::TestDdlSchema::test_raw_sql_create_table_email_fires
- tests/test_pii_structural_gate.py::TestDdlSchema::test_raw_sql_create_table_unrelated_columns_do_not_fire
- tests/test_pii_structural_gate.py::TestDdlSchema::test_orm_column_unrelated_field_does_not_fire
designated_repro_test: null
threat: null
component: null
---
T-0207 follow-on: CREATE TABLE / column DDL in migrations (alembic, raw SQL) and sqlalchemy Column(...) ORM models scanned with the FIELD_SIGNATURES keyword+type table (frob.gates._pii_structural). Deferred from T-0207's scope (Python data-structure fields + env access only).

CORPUS UNIVERSE ADDITION (2026-07-20): the code-level performance corpus (docs/design/coding-performance-corpus.md -- conceptual/algorithmic + low-level/mechanical-sympathy) and the system-performance corpus (docs/design/system-performance-corpus.md -- USE/RED methods, profiling, queueing/USL, latency/coordinated-omission, capacity planning) join the registry universe on the same terms: each emits a DENOMINATOR MANIFEST, is folded into docs/design/registry/ (perf.yaml), reconciled against src/frob/perf's PERF rules, and every entry gets a disposition. They feed the arch/perf-check side of the exhaustiveness drift-lock (T-0343).