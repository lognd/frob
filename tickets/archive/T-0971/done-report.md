## Done report

Changed:
src/frob/gates/_pii_structural.py::_camel_to_snake
src/frob/gates/_pii_structural.py::_CAMEL_BOUNDARY_RE
src/frob/gates/_pii_structural.py::_field_name_hit
src/frob/gates/_pii_structural.py::_STRUCTURE_BASE_NAMES
src/frob/gates/_pii_structural.py::_PII012_REVIEWED_NON_PII
tests/test_pii_structural_gate.py::TestFieldNames.test_camelcase_password_hash_field_fires
tests/test_pii_structural_gate.py::TestFieldNames.test_camelcase_date_of_birth_field_fires
tests/test_pii_structural_gate.py::TestFieldNames.test_orm_declarative_base_field_fires
tests/test_pii_structural_gate.py::TestFieldNames.test_django_model_field_fires
frob.toml [gates.severity] PII010/PII012 = "error"

Cluster table (167 unwaived PII010/PII012 findings, measured baseline 2026-07-27):

| Cluster | Count | Root cause | Disposition |
|---|---|---|---|
| PII012 "token" homonym | 150 | Lexer/parser/regex-name/CLI-invocation/ContextVar/random-nonce use of "token" across strata provability modules (`_*_TOKEN_RE` compiled patterns), `frob.arch`/`frob.gates`/`frob.graph` tree-sitter+markdown+CLI parsing, and a `uuid4().hex` nonce -- never an auth token. Same class T-0540 already established for 60 sibling sites. | Extended `_PII012_REVIEWED_NON_PII` frozenset with 68 new (file, identifier) tuples after individually reading each site (module docstring block updated to record the T-0971 batch). |
| PII012 "diagnosis" homonym | 10 | `frob doctor`'s own self-diagnostic feature name (`test_run_diagnosis_*`), not patient health data. | Same frozenset, T-0540-precedent single-site tuples (10 entries). |
| PII012 gate-self-test names (email/password/token/ssn/secret) | 7 | `tests/test_gates.py` test functions that literally test PII010's own TS/Rust field-shape detection (`test_ts_interface_email_field_fires`, etc.) -- self-pattern match, file too broad for the whole-file `_PII_SELF_PATTERN_SUFFIXES` list. | Same frozenset, 7 per-function tuples. |
| PII012 plain-English comment word ("address") / lexer comment ("token") in test_ticket_land.py | 2 | Ordinary prose ("must address the ticket by its...") and a "T-draft- token" parsing reference, read in context. | Same frozenset, 2 tuples. |
| PII010 "passwd"/"passwd_added"/"passwd_removed" | 3 (already waived) | Raw `/etc/passwd` audit-diff text, not parsed PII. | Pre-existing `frob:waive PII010` comments in `src/frob/deploy/_audit.py`; confirmed still correctly discharged (severity=note, `[waived: ...]` suffix) -- no change needed. |
| Audit finding 5 (camelCase blindness) | design gap | `_field_name_hit` only split on `_`, missing `passwordHash`/`dateOfBirth`-shaped fields. | Fixed at the root: `_camel_to_snake` (new, `_CAMEL_BOUNDARY_RE`) normalizes camelCase/acronym boundaries to `_` before the existing lower+split/substring logic runs -- one shared normalization for both the single-word and multi-word keyword paths, not two. New tests: `test_camelcase_password_hash_field_fires`, `test_camelcase_date_of_birth_field_fires`. |
| Audit finding 14 (ORM-base blindness) | design gap | `_is_data_structure` only recognized `BaseModel`/`TypedDict`/`NamedTuple`/`dataclass`/`attrs`, missing SQLAlchemy/Django ORM rows -- the most common real PII carrier. | `_STRUCTURE_BASE_NAMES` extended with `DeclarativeBase` and `Model` (both fixed, well-known library base names, direct-subclass match). New tests: `test_orm_declarative_base_field_fires`, `test_django_model_field_fires`. Disclosed remaining gap: a THIRD-hop project-local intermediate base (`class User(OrmBase)`) is not resolved -- needs cross-file transitive base resolution outside this single-file AST gate's scope; documented in the module comment, not silently dropped. |

Promotion state: `frob.toml` `[gates.severity]` now sets `PII010 = "error"` and `PII012 = "error"` (T-0756 acceptance policy). Repo measured at 0 unwaived PII010/PII012 findings after the fix (`gate:PII 0 errors, 0 warnings, 3 waived` on `frob check --only gates-security`), so the promotion does not immediately red the build.

Test evidence:
- `pytest -q tests/test_pii_structural_gate.py` -- 104/104 pass (incl. 4 new tests, drift-lock parametrization over `FIELD_SIGNATURES` unaffected).
- `frob test --base main` (touched-set) -- python exit=0, 4/4 outcomes recorded (`tests/test_gates.py::test_gates_run_gates_integration`, `tests/test_pii_structural_gate.py` full module + 2 individually-selected new cases).
- `frob check --ticket T-0971 --only gates-fast/gates-native/gates-security/lint/static` (chunked per playbook section 3b) -- 0 errors on every stage; `ruff-format` flagged 3 pre-existing, out-of-scope files (`src/frob/arch/_lock_ordering.py`, `tests/test_ticket_land.py`, `tests/unit/test_arch.py`) unrelated to this change, left untouched.

Filed: none (the 167 findings resolved within scope; no remainder child needed).

Gates: `frob check --ticket T-0971` clean across all 5 stage groups (gates-fast, gates-native, gates-security, lint, static) -- 0 errors, no new waivers added beyond the reviewed-non-PII frozenset entries (which are the sanctioned discharge mechanism for this exact class, T-0540 precedent).

### Changed
(no changed files detected)

### Evidence
- `tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_password_hash_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestFieldNames::test_camelcase_date_of_birth_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestFieldNames::test_orm_declarative_base_field_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestFieldNames::test_django_model_field_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 0 error(s), 4939 warning(s), 220 waived
- error-findings: none (measured, zero errors)
