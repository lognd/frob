## Done report

Changed:
- src/frob/gates/_arch_schema.py (new): _ARCH_DEFAULT_KEYS,
  arch_known_keys, _unresolved, _unknown_key_violation,
  _resolve_known_keys, _arch_table, arch_schema_gate
- src/frob/gates/__init__.py: wired arch_schema_gate into _ALL_GATES,
  _CANONICAL_GATE_ORDER, _build_process_jobs, __all__
- src/frob/gates/_waive.py: registered ARCHSCHEMA001 in
  _KNOWN_GATE_RULES
- src/frob/check/__init__.py: added "arch_schema" to the thread-pool
  stage group
- frob.toml: declared [arch_schema] known_keys =
  "frob.gates._arch_schema:arch_known_keys"
- docs/modules/gates.md: rule catalog row + ARCHSCHEMA001 section
- docs/design/registry/check-coverage.yaml: CHK-GATE-ARCHSCHEMA001
  entry, gate_rule_total 319 -> 320
- tests/unit/test_arch_table_schema.py (new): 9 tests
- pyproject.toml / .frob-release.json / CHANGELOG.md / uv.lock: REL001
  version bump to 0.520.0

Component-membership check (per the T-2429 design note, applied here as
instructed): `frob.repo_meta.load_arch_config` (the [arch] reader) lives
in a DIFFERENT strata component from `frob.gates`. I initially drafted
`arch_known_keys` importing `load_arch_config`'s own ARCH_DEFAULT_*
constants directly to avoid a second hand-maintained copy -- caught
before landing that this reintroduces exactly T-2429's cross-component
Flow problem (gates -> core), so the known-key set is instead a plain
hardcoded literal tuple of the 10 key NAMES in src/frob/gates/
_arch_schema.py, same-component with every wiring site, consistent with
every other T-2390 child except T-2432 (whose TestPolicy model lives IN
frob.gates._models, same component, so importing there is fine).

Must-still-pass control caught a genuine near-miss (not a real repo
defect): [arch.layering] (T-0620's DIP layering contract) is a real,
documented, deliberately-inert nested sub-table with a completely
different schema (layers/allow), one level inside [arch]. An initial
version of the gate flagged "layering" as an undeclared [arch] key
against this repo's own real frob.toml. Fixed in the detector (excluding
dict-valued keys from consideration, the same table-vs-scalar exclusion
TOPSCALARSCHEMA001 already uses) rather than by special-casing "layering"
by name or weakening the check -- covered by its own dedicated
must-still-pass fixture (test_nested_layering_subtable_is_never_flagged).

Evidence: tests/unit/test_arch_table_schema.py::TestArchSchemaGate::{
test_arch_known_keys_matches_load_arch_configs_own_defaults,
test_must_now_fire_reports_the_undeclared_key,
test_must_still_pass_this_repos_own_frob_toml,
test_nested_layering_subtable_is_never_flagged,
test_no_schema_declared_is_unresolved_not_empty,
test_unresolvable_schema_dotted_path_is_unresolved,
test_non_set_non_callable_schema_value_is_unresolved,
test_no_frob_toml_is_unresolved,
test_no_arch_table_at_all_is_clean_not_error}

Fixtures:
- must-now-fire: the epic's own filing-time example, "max_fuction_lines"
  typo alongside a valid max_class_methods key -- reported as one ERROR.
- must-still-pass: this repo's own frob.toml, the real [arch] table (5
  of 10 known keys set) PLUS the real [arch.layering] sub-table -- zero
  findings.

No genuinely undeclared LEAF key exists in this repo's real [arch]
table; [arch.layering] is a real, documented, different-schema
sub-table, not an undeclared key of load_arch_config's own set.

Filed: none (no out-of-scope work discovered; the layering false-positive
was a bug in this ticket's OWN new detector, caught and fixed before
evidence was bound)

Gates: schema module lives in src/frob/gates/ (same-component as every
wiring site, deliberately NOT importing frob.repo_meta's constants per
the component-membership check above). Repo-wide pre-existing
gate:SELFAUDIT/ARCH/COV/DOC/DRIFT/PERF/PRE/RENDER/SEC/TICK/WIRE failures
are unrelated to this ticket's touched set, consistent with every prior
T-2390 child.

### Changed
```
 docs/design/registry/check-coverage.yaml |   7 +-
 docs/modules/gates.md                    |  39 +++++-
 frob.toml                                |  10 ++
 src/frob/check/__init__.py               |   2 +
 src/frob/gates/__init__.py               |   8 ++
 src/frob/gates/_arch_schema.py           | 231 +++++++++++++++++++++++++++++++
 src/frob/gates/_waive.py                 |   4 +
 tests/unit/test_arch_table_schema.py     | 179 ++++++++++++++++++++++++
 tickets/T-2433/ticket.md                 |  97 ++++++++++++-
 9 files changed, 573 insertions(+), 4 deletions(-)
```

### Evidence
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_arch_known_keys_matches_load_arch_configs_own_defaults` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_nested_layering_subtable_is_never_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_non_set_non_callable_schema_value_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_arch_table_schema.py::TestArchSchemaGate::test_no_arch_table_at_all_is_clean_not_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 9 passed (from 9 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, DUP001@src/frob/gates/_arch_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2433, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE001@src/frob/gates/_arch_schema.py, WIRE003@docs/modules/cli.md
