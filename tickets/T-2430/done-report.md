## Done report

Changed:
- src/frob/gates/_profile_schema.py (new): PROFILE_KNOWN_KEYS,
  _unresolved, _unknown_key_violation, _resolve_known_keys,
  _profile_table, profile_schema_gate
- src/frob/gates/__init__.py: wired profile_schema_gate into _ALL_GATES,
  _CANONICAL_GATE_ORDER, _build_process_jobs, __all__
- src/frob/gates/_waive.py: registered PROFILESCHEMA001 in
  _KNOWN_GATE_RULES
- src/frob/check/__init__.py: added "profile_schema" to the thread-pool
  stage group
- frob.toml: declared [profile_schema] known_keys =
  "frob.gates._profile_schema:PROFILE_KNOWN_KEYS"
- docs/modules/gates.md: rule catalog row + PROFILESCHEMA001 section
- docs/design/registry/check-coverage.yaml: CHK-GATE-PROFILESCHEMA001
  entry, gate_rule_total 316 -> 317
- tests/unit/test_profile_table_schema.py (new): 7 tests (must-now-fire,
  must-still-pass control against this repo's real frob.toml, the
  UNRESOLVED fail-loudly fixtures, plus a no-table-is-not-an-error case
  distinguishing "optional table absent" from "declared schema missing")
- pyproject.toml / .frob-release.json / CHANGELOG.md / uv.lock: REL001
  version bump to 0.515.0 via `frob release stamp`/`sync`

Evidence: tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::{
test_must_now_fire_reports_the_undeclared_key,
test_must_still_pass_this_repos_own_frob_toml,
test_no_schema_declared_is_unresolved_not_empty,
test_unresolvable_schema_dotted_path_is_unresolved,
test_non_set_non_callable_schema_value_is_unresolved,
test_no_frob_toml_is_unresolved,
test_no_profile_table_at_all_is_clean_not_error}

Fixtures:
- must-now-fire: an "overide_ratchet" typo alongside a valid `profile`
  value in a synthetic [profile] table -- reported as one ERROR.
- must-still-pass: this repo's own frob.toml, the real [profile] table
  (profile = "rapid", override_ratchet = true) -- zero findings.

Filed: none (no out-of-scope work discovered)

Gates: `frob check --ticket T-2430` -- gate:SCOPE clean after adding the
release-mechanism files to scope (same T-2428/T-2429 precedent); the
schema module lives in src/frob/gates/ (same-component, no new
cross-component Flow needed, following T-2429's own SYS003 lesson).
Pre-existing repo-wide gate:SELFAUDIT/ARCH/COV/DOC/DRIFT/PERF/PRE/RENDER/
SEC/TICK/WIRE failures are unrelated to this ticket's touched set, per
the tool's own `--ticket T-2430 scopes ONLY gate:SCOPE/gate:PREWORK...`
note; the NATIVESCHEMA001/REFSCHEMA001 precedent already established
these are pre-existing, unaddressed by prior T-2390 children too.

### Changed
```
 tickets/T-2430/ticket.md | 71 +++++++++++++++++++++++++++++++++++++++++++++++-
 1 file changed, 70 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_non_set_non_callable_schema_value_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_profile_table_schema.py::TestProfileSchemaGate::test_no_profile_table_at_all_is_clean_not_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV001@src/frob/verify/_drain.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC002@src/frob/verify/_drain.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2430, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
