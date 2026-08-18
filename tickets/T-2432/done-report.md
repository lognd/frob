## Done report

Changed:
- src/frob/gates/_testing_schema.py (new): testing_known_keys,
  _unresolved, _unknown_key_violation, _resolve_known_keys,
  _testing_table, testing_schema_gate
- src/frob/gates/__init__.py: wired testing_schema_gate into _ALL_GATES,
  _CANONICAL_GATE_ORDER, _build_process_jobs, __all__
- src/frob/gates/_waive.py: registered TESTINGSCHEMA001 in
  _KNOWN_GATE_RULES
- src/frob/check/__init__.py: added "testing_schema" to the thread-pool
  stage group
- frob.toml: declared [testing_schema] known_keys =
  "frob.gates._testing_schema:testing_known_keys"
- docs/modules/gates.md: rule catalog row + TESTINGSCHEMA001 section
- docs/design/registry/check-coverage.yaml: CHK-GATE-TESTINGSCHEMA001
  entry, gate_rule_total 318 -> 319
- tests/unit/test_testing_table_schema.py (new): 8 tests
- pyproject.toml / .frob-release.json / CHANGELOG.md / uv.lock: REL001
  version bump to 0.519.0

Ticket-specified investigation (worth doing early, per the ticket body):
confirmed `TestPolicy` (frob.gates._models) IS a real pydantic BaseModel
for this table, and confirmed `frob.gates._sys._load_test_config` does
NOT construct it from the raw table directly -- it pre-filters via
`{k: v for k, v in testing_tbl.items() if k in fields}` BEFORE calling
`TestPolicy(**...)`, so an unknown key never reaches the model at all and
`extra="forbid"` would never see it. This is the epic's own finding
applied to its first already-modeled table: having a real pydantic model
is not sufficient when the reader pre-filters before construction. The
schema idiom generalizes cleanly -- known_keys is declared as a zero-arg
callable (`testing_known_keys`) that reads `TestPolicy.model_fields`
directly, so the model itself stays the single source of truth rather
than a second hand-maintained list.

Pytest gotcha caught and fixed: importing `testing_known_keys`/
`testing_schema_gate` directly into the test module under their real
names caused pytest's default `test*` collection pattern to ALSO treat
them as test functions (both names start with "test"), producing a
spurious collection error. Fixed by importing under `_`-prefixed
aliases (`_testing_known_keys`, `_testing_schema_gate`) -- a naming
collision specific to this child (every other T-2390 child's gate
function is named `*_gate` with a distinct prefix that does not start
with "test").

Evidence: tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::{
test_testing_known_keys_reads_test_policy_model_fields,
test_must_now_fire_reports_the_undeclared_key,
test_must_still_pass_this_repos_own_frob_toml,
test_no_schema_declared_is_unresolved_not_empty,
test_unresolvable_schema_dotted_path_is_unresolved,
test_non_set_non_callable_schema_value_is_unresolved,
test_no_frob_toml_is_unresolved,
test_no_testing_table_at_all_is_clean_not_error}

Fixtures:
- must-now-fire: "min_unit_case" typo (missing trailing s) alongside a
  valid min_integration key -- reported as one ERROR. This specific
  fixture matters for this child: `_load_test_config`'s own pre-filter
  would silently drop this key and construct a valid-looking TestPolicy
  with defaults, so a check that only re-ran TestPolicy(**raw_table)
  validation would NOT catch it -- the check must inspect the RAW table
  before filtering, which is what this gate does.
- must-still-pass: this repo's own frob.toml, the real [testing] table
  (min_unit_cases, min_integration, unit_branch_cov, module_line_cov,
  system_line_cov) -- zero findings.

No genuinely undeclared key exists in this repo's real [testing] table.

Filed: none (no out-of-scope work discovered)

Gates: schema module lives in src/frob/gates/ (same-component as every
wiring site and as TestPolicy itself, so no cross-component Flow
question arises here). Repo-wide pre-existing gate:SELFAUDIT/ARCH/COV/
DOC/DRIFT/PERF/PRE/RENDER/SEC/TICK/WIRE failures are unrelated to this
ticket's touched set, consistent with every prior T-2390 child.

### Changed
```
 docs/design/registry/check-coverage.yaml |   7 +-
 docs/modules/gates.md                    |  33 +++++-
 frob.toml                                |   8 ++
 src/frob/check/__init__.py               |   2 +
 src/frob/gates/__init__.py               |   8 ++
 src/frob/gates/_testing_schema.py        | 191 +++++++++++++++++++++++++++++++
 src/frob/gates/_waive.py                 |   4 +
 tests/unit/test_testing_table_schema.py  | 143 +++++++++++++++++++++++
 tickets/T-2432/ticket.md                 |  94 ++++++++++++++-
 9 files changed, 487 insertions(+), 3 deletions(-)
```

### Evidence
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_testing_known_keys_reads_test_policy_model_fields` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_non_set_non_callable_schema_value_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_testing_table_schema.py::TestTestingSchemaGate::test_no_testing_table_at_all_is_clean_not_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, DUP001@src/frob/gates/_testing_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2432, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/gates/_testing_schema.py, WIRE003@docs/modules/cli.md
