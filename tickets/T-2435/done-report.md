## Done report

Changed:
- src/frob/gates/_gates_schema.py (new)
- src/frob/gates/__init__.py (wiring)
- src/frob/check/__init__.py (wiring)
- frob.toml ([gates.ratchet] ratchet_known_keys declaration)
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml

Evidence: 7/7 pytest node ids under tests/unit/test_gates_table_schema.py::TestGatesSchemaGate,
including test_must_still_pass_this_repos_own_frob_toml (zero findings against this repo's
real frob.toml) and two must-now-fire fixtures (undeclared ratchet key, unregistered severity
rule id). All 7 pass. GATESSCHEMA001 rule id confirmed already registered in
src/frob/gates/_waive.py on main (T-2441 landed it as a disclosed cross-ticket courtesy) --
no scope widen to _waive.py needed for this land.

Filed: none

Gates: frob check --only gates-fast --ticket T-2435 -- gates_schema/test_runner_schema/
dup_schema/graph_schema all report 0 findings against this repo's real frob.toml; other FAIL
lines in that run are pre-existing repo-wide findings unrelated to this ticket's scope (per
the tool's own gate:scope-note disclosure).

### Changed
```
 docs/design/registry/check-coverage.yaml  |  22 ++-
 docs/modules/gates.md                     |  93 ++++++++++-
 frob.toml                                 |  30 ++++
 src/frob/check/__init__.py                |   7 +
 src/frob/gates/__init__.py                |  28 ++++
 src/frob/gates/_dup_graph_schema.py       | 254 +++++++++++++++++++++++++++++
 src/frob/gates/_gates_schema.py           | 255 ++++++++++++++++++++++++++++++
 src/frob/gates/_test_runner_schema.py     | 206 ++++++++++++++++++++++++
 tests/unit/test_dup_graph_table_schema.py | 135 ++++++++++++++++
 tests/unit/test_gates_table_schema.py     | 133 ++++++++++++++++
 tests/unit/test_test_table_schema.py      | 139 ++++++++++++++++
 tickets/T-2435/ticket.md                  |  74 ++++++++-
 tickets/T-2436/ticket.md                  |  83 +++++++++-
 tickets/T-2437/ticket.md                  |  66 +++++++-
 14 files changed, 1519 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_now_fire_reports_the_undeclared_ratchet_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_now_fire_reports_the_unregistered_severity_rule_id` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_ratchet_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_unresolvable_ratchet_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_gates_table_schema.py::TestGatesSchemaGate::test_no_gates_table_at_all_is_clean_not_error` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, DRIFT002@tests/test_gates.py, DUP001@src/frob/gates/_test_runner_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_mutate.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2435, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE003@docs/modules/cli.md
