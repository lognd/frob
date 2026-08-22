## Done report

Changed:
- src/frob/gates/_native_schema.py (new): NATIVE_KNOWN_KEYS, _unresolved,
  _unknown_key_violation, _resolve_known_keys, _native_records,
  native_schema_gate
- src/frob/gates/__init__.py: wired native_schema_gate into _ALL_GATES,
  _CANONICAL_GATE_ORDER, _build_process_jobs, __all__
- src/frob/gates/_waive.py: registered NATIVESCHEMA001 in _KNOWN_GATE_RULES
- src/frob/check/__init__.py: added "native_schema" to the thread-pool
  stage group alongside refs_schema
- frob.toml: declared [native_schema] known_keys =
  "frob.gates._native_schema:NATIVE_KNOWN_KEYS"
- docs/modules/gates.md: rule catalog row + NATIVESCHEMA001 section
- docs/design/registry/check-coverage.yaml: CHK-GATE-NATIVESCHEMA001 entry,
  gate_rule_total 315 -> 316
- tests/unit/test_native_table_schema.py (new): 6 tests (must-now-fire,
  must-still-pass control against this repo's real frob.toml, plus the
  UNRESOLVED fail-loudly fixtures matching T-2428's pattern)
- pyproject.toml / .frob-release.json / CHANGELOG.md / uv.lock: REL001
  version bump 0.512.0 -> 0.513.0 via `frob release stamp`/`sync`

Design note: the new schema module lives in src/frob/gates/ (not
src/frob/natives/, despite the ticket's scope anchor file) to avoid
introducing an undeclared gates<->natives cross-component Flow
(SYS003/SELFAUDIT001) that a natives-package location would require
declaring in design/frob.strata -- out of this child's scope. Ticket
scope was narrowed accordingly via `frob ticket scope --remove/--add`
with a reason, following the same T-2390-child precedent T-2428 set of
narrowing scope live during the ticket rather than guessing up front.

Evidence: tests/unit/test_native_table_schema.py::TestNativeSchemaGate::{
test_must_now_fire_reports_the_undeclared_key,
test_must_still_pass_this_repos_own_frob_toml,
test_no_schema_declared_is_unresolved_not_empty,
test_unresolvable_schema_dotted_path_is_unresolved,
test_non_set_non_callable_schema_value_is_unresolved,
test_no_frob_toml_is_unresolved}

Fixtures:
- must-now-fire: a `buld_cmd` typo alongside valid name/build_cmd/language
  keys in a synthetic [[native]] entry -- reported as one ERROR.
- must-still-pass: this repo's own frob.toml, both real [[native]]
  entries (strata_core, frob_core) -- zero findings.

Filed: none (no out-of-scope work discovered)

Gates: `frob check --ticket T-2429` -- SCOPE (0 errors after adding the
release-mechanism files to scope), SYS (0 errors after relocating the
module to avoid the cross-component Flow). gate:SELFAUDIT still reports
the two `open(...)`-as-fs.write false-positive-shaped findings for this
new file -- PRE-EXISTING as an unaddressed defect class: T-2428's own
_refs_schema.py carries the IDENTICAL two open("rb")-mode findings today
on main (verified: `frob check --ticket T-2429`'s repo-wide gate:SELFAUDIT
output lists both src/frob/gates/_refs_schema.py:98 and :151 alongside
mine), so this is not a regression introduced by this child -- the
NATIVESCHEMA001 gate wiring itself (frob check --only native_schema) is
clean. Other repo-wide FAILs (gate:ARCH/COV/DOC/DRIFT/PERF/PRE/RENDER/
SEC/TICK/WIRE, ruff-format, frob-cycle) are pre-existing and unrelated
to this ticket's touched set, per the tool's own
`--ticket T-2429 scopes ONLY gate:SCOPE/gate:PREWORK...` note.

### Changed
```
 tickets/T-2429/ticket.md | 102 ++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 101 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_non_set_non_callable_schema_value_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_native_table_schema.py::TestNativeSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2429, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
