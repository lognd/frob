## Done report

Changed:
- src/frob/gates/_pii_structural.py: PII010 now scans (T-0348 family 2, DB/DDL schema):
  `_is_column_call`, `_column_call_string_name`, `_scan_orm_columns` (sqlalchemy
  declarative `name = Column(...)` and alembic-style positional
  `Column("name", ...)`), `_split_top_level_commas`, `_ddl_column_names`,
  `_scan_ddl_strings` (raw-SQL `CREATE TABLE(...)` string literals), and the new
  `_scan_python_ddl` entrypoint wired into `pii_structural_gate`. All reuse the
  existing `FIELD_SIGNATURES`/`_field_name_hit` single-source registry, no second
  table.
- tests/test_pii_structural_gate.py: new `TestDdlSchema` class (5 cases: ORM
  column fires, alembic positional-arg column fires, raw-SQL CREATE TABLE fires,
  raw-SQL CREATE TABLE with unrelated columns does not fire, ORM column with
  unrelated field does not fire).
- docs/modules/gates.md: documented the family-2 extension under the existing
  "Structural PII secrets detection T-0207" section.

Evidence:
- tests/test_pii_structural_gate.py::TestDdlSchema::test_orm_column_password_fires
- tests/test_pii_structural_gate.py::TestDdlSchema::test_alembic_positional_column_ssn_fires
- tests/test_pii_structural_gate.py::TestDdlSchema::test_raw_sql_create_table_email_fires
- tests/test_pii_structural_gate.py::TestDdlSchema::test_raw_sql_create_table_unrelated_columns_do_not_fire
- tests/test_pii_structural_gate.py::TestDdlSchema::test_orm_column_unrelated_field_does_not_fire
- Full-file run: `uv run pytest tests/test_pii_structural_gate.py tests/test_secrets_gate.py -q` -> 142 passed
- `uv run frob test --base main` -> [PASS] python exit=0

Filed: none (no out-of-scope work found)

Scope note: T-0455's scope-hygiene pass had narrowed this ticket's test-file
scope to tests/test_gates.py (the wrong mirrored path -- T-0207's actual
evidence lives in tests/test_pii_structural_gate.py). Corrected via
`frob ticket scope T-0348 --add tests/test_pii_structural_gate.py --reason ...`
before touching the test file; recorded in the ticket's scope_changes audit
trail. Filed no separate ticket for this since `frob ticket scope` is the
built-in self-serve correction mechanism and the same wrong-path narrowing
affects the sibling T-0349/T-0350/T-0351 tickets, corrected the same way per
ticket as each is started (sequential leases prevent doing all four upfront).

Gates: `uv run frob check --delta --ticket T-0348` clean (0 errors, 2
pre-existing WARN-severity waived findings unrelated to this change). ruff
check/format and ty both clean.

### Changed
(no changed files detected)

### Evidence
- `tests/test_pii_structural_gate.py::TestDdlSchema::test_orm_column_password_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestDdlSchema::test_alembic_positional_column_ssn_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestDdlSchema::test_raw_sql_create_table_email_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestDdlSchema::test_raw_sql_create_table_unrelated_columns_do_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestDdlSchema::test_orm_column_unrelated_field_does_not_fire` (pytest node id, verified passing when recorded)
