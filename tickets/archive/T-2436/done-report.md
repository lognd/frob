## Done report

Changed:
- src/frob/gates/_test_runner_schema.py (new)
- src/frob/gates/__init__.py (wiring)
- src/frob/check/__init__.py (wiring)
- frob.toml ([test] known_keys declaration)
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml

Note: this ticket's code was already carried onto main as a disclosed passenger of T-2435's
land (--allow-cross-ticket, same series worktree per T-1618) -- this Done report/evidence/
land formally closes T-2436's own ticket state; no new code changes here.

Evidence: 6/6 pytest node ids under tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate,
including test_must_still_pass_this_repos_own_frob_toml (zero findings against this repo's
real frob.toml). TESTRUNNERSCHEMA001 rule id confirmed already registered in
src/frob/gates/_waive.py on main (T-2441 landed it as a disclosed cross-ticket courtesy) --
no scope widen to _waive.py needed.

Filed: none

Gates: frob check --only gates-fast --ticket T-2435 (run earlier in this series) showed
test_runner_schema reporting 0 findings against this repo's real frob.toml.

### Changed
```
 tickets/T-2436/ticket.md | 9 +++++++++
 1 file changed, 9 insertions(+)
```

### Evidence
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_unresolvable_schema_dotted_path_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_non_set_non_callable_schema_value_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_test_table_schema.py::TestTestRunnerSchemaGate::test_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2436, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE003@docs/modules/cli.md


frob:waive BUG002 reason="this bug-kind ticket's own diff-touched code (src/frob/gates/_test_runner_schema.py) already landed on main as a disclosed passenger of T-2435's cross-ticket land (--allow-cross-ticket, same series worktree, T-1618) -- there is no separate parent commit where this fix is absent to reproduce a repro-fail against; the fix and the bound test's passing state are already atomically merged into main's history"
