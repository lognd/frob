## Done report

Changed:
- src/frob/gates/_toplevel_scalar_schema.py (new): TOPLEVEL_SCALAR_KNOWN_KEYS,
  _unresolved, _unknown_key_violation, _resolve_known_keys,
  _toplevel_scalar_keys, toplevel_scalar_schema_gate
- src/frob/gates/__init__.py: wired toplevel_scalar_schema_gate into
  _ALL_GATES, _CANONICAL_GATE_ORDER, _build_process_jobs, __all__
- src/frob/gates/_waive.py: registered TOPSCALARSCHEMA001 in
  _KNOWN_GATE_RULES
- src/frob/check/__init__.py: added "toplevel_scalar_schema" to the
  thread-pool stage group
- frob.toml: declared [toplevel_scalar_schema] known_keys =
  "frob.gates._toplevel_scalar_schema:TOPLEVEL_SCALAR_KNOWN_KEYS"
- docs/modules/gates.md: rule catalog row + TOPSCALARSCHEMA001 section
- docs/design/registry/check-coverage.yaml: CHK-GATE-TOPSCALARSCHEMA001
  entry, gate_rule_total 317 -> 318
- tests/unit/test_toplevel_scalar_schema.py (new): 7 tests
- pyproject.toml / .frob-release.json / CHANGELOG.md / uv.lock: REL001
  version bump to 0.518.0

Structural note (per ticket body): this table is a flat set of bare
top-level scalar keys, not a `[table]` to iterate -- the schema
declaration lives in its own `[toplevel_scalar_schema]` sub-table
(kept OUT of the document root so the declaration key itself is never
confused with the scalars it describes), and the key-extraction logic
must exclude BOTH `[table]` headers (dict-valued) AND
`[[array-of-tables]]` headers (list-of-dict-valued, e.g. this repo's own
`[[native]]`) -- an early version of `_toplevel_scalar_keys` only
excluded dicts and misclassified `[[native]]` as an undeclared top-level
scalar named "native" against this repo's OWN real frob.toml (caught by
the must-still-pass control itself, which is exactly what that control
is for -- fixed in the detector, not by weakening the check or excluding
"native" specifically).

Evidence: tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::{
test_must_now_fire_reports_the_undeclared_key,
test_must_still_pass_this_repos_own_frob_toml,
test_no_schema_declared_is_unresolved_not_empty,
test_unresolvable_schema_dotted_path_is_unresolved,
test_non_set_non_callable_schema_value_is_unresolved,
test_no_frob_toml_is_unresolved,
test_table_headers_are_never_flagged}

Fixtures:
- must-now-fire: a "min_frob_verison" typo alongside a valid check_base
  scalar and an unrelated [arch] table -- reported as one ERROR.
- must-still-pass: this repo's own frob.toml -- both real top-level
  scalars (min_frob_version, check_base) plus every real [table]/
  [[array-of-tables]] header (including [[native]]) -- zero findings.

No genuinely undeclared top-level scalar key exists in this repo's real
frob.toml.

Filed: none (no out-of-scope work discovered; the [[native]]
misclassification was a bug in this ticket's OWN new detector, caught
and fixed before evidence was bound, not a separate ticket-worthy find)

Gates: schema module lives in src/frob/gates/ (same-component as every
wiring site, per the T-2429 design note). Repo-wide pre-existing
gate:SELFAUDIT/ARCH/COV/DOC/DRIFT/PERF/PRE/RENDER/SEC/TICK/WIRE failures
are unrelated to this ticket's touched set, consistent with every prior
T-2390 child in this series.

### Changed
```
 docs/design/registry/check-coverage.yaml  |   7 +-
 docs/modules/gates.md                     |  34 ++++-
 frob.toml                                 |   8 ++
 src/frob/check/__init__.py                |   2 +
 src/frob/gates/__init__.py                |   8 ++
 src/frob/gates/_toplevel_scalar_schema.py | 211 ++++++++++++++++++++++++++++++
 src/frob/gates/_waive.py                  |   4 +
 tests/unit/test_toplevel_scalar_schema.py | 163 +++++++++++++++++++++++
 tickets/T-2431/ticket.md                  |  95 +++++++++++++-
 9 files changed, 528 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_non_set_non_callable_schema_value_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_toplevel_scalar_schema.py::TestTopLevelScalarSchemaGate::test_table_headers_are_never_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2431, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
