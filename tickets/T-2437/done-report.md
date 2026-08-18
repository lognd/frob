## Done report

Changed:
- src/frob/gates/_dup_graph_schema.py (new)
- src/frob/gates/__init__.py (wiring)
- src/frob/check/__init__.py (wiring)
- frob.toml ([dup] known_keys, [graph] known_keys declarations)
- docs/modules/gates.md
- docs/design/registry/check-coverage.yaml

Two genuinely disjoint readers ([dup] frob.gates._dup._dup_config, [graph] frob.excludes)
combined into one module per the ticket's own scoping note, kept in clearly separated
sections/fixtures for a mechanical future split.

Note: this ticket's code was already carried onto main as a disclosed passenger of T-2435's
land (--allow-cross-ticket, same series worktree per T-1618) -- this Done report/evidence/
land formally closes T-2437's own ticket state; no new code changes here.

Evidence: 8/8 pytest node ids under tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate
(4 dup-table + 4 graph-table cases), including both must-still-pass-this-repo's-own-frob.toml
fixtures (zero findings against the real frob.toml) and both must-now-fire fixtures.
DUPSCHEMA001/GRAPHSCHEMA001 rule ids confirmed already registered in src/frob/gates/_waive.py
on main (T-2441 landed them as a disclosed cross-ticket courtesy) -- no scope widen to
_waive.py needed.

Known gap being handled in the same land window, not duplicated here: _dup_graph_schema.py's
only filesystem access is toml_path.open("rb") (a read) in both TOML-loading call sites; the
dangerous-ops table's ("open(", ".write(") needle pair matches on bare "open(" presence alone
(mode argument never consulted), so this read-only module trips the fs.write capability
detector -- same pre-existing detector imprecision already present (and already declared, with
the same false-positive shape) in all four prior T-2390 sibling schema modules. The design/
frob.strata declaration for this module is being added by T-2453's agent (which holds the live
lease on that file) in the same pass as T-2435/T-2436's identical gap, per coordinator
direction; the root-cause detector fix is filed as T-2457 (kind=security), whose acceptance
requires removing all seven false declarations once the needle-match imprecision is fixed.

Filed: none (T-2457 filed by the coordinator, not this ticket)

Gates: frob check --only gates-fast --ticket T-2435 (run earlier in this series) showed
dup_schema/graph_schema reporting 0 findings against this repo's real frob.toml.

### Changed
```
 tickets/T-2436/done-report.md | 43 +++++++++++++++++++++++++++++++++++++++++++
 tickets/T-2436/ticket.md      |  9 +++++++++
 tickets/T-2437/ticket.md      | 11 +++++++++++
 3 files changed, 63 insertions(+)
```

### Evidence
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_dup_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_must_now_fire_reports_the_undeclared_key` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_must_still_pass_this_repos_own_frob_toml` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_no_schema_declared_is_unresolved_not_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_graph_table_schema.py::TestDupGraphSchemaGate::test_graph_no_frob_toml_is_unresolved` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@.claude/hooks/root-write-guard.py, ARCH103@src/frob/release/_cli.py, COV001@src/frob/gates/_port_selfcheck.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_port_selfcheck.py, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC007@tests/test_gates.py, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, DOCENUM001@docs/modules/gates.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/gates/_fix_engine.py, DRIFT002@docs/modules/arch.md, DRIFT002@docs/modules/vet.md, DRIFT002@tests/test_gates.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/app/ticket_runner/_query.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/__init__.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/gates/_dup_graph_schema.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/verify/_worker.py, F401@/home/logan/projects/frob/.claude/worktrees/t-2390-series/src/frob/vet/_capability.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PRE001@tickets/T-2437, RENDER001@src/frob/release/_cli.py, SEC110@.claude/hooks/root-write-guard.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, TICK006@tickets.md, WIRE003@docs/modules/cli.md
