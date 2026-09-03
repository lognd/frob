## Done report

T-3467: moved the T-2114/ARCH001-diff pure logic (new-public-symbol doc/test-edge check, diff-scoped ARCH001 long-function check, and shared helpers) out of frob.app.ticket_runner._land_cmd and into frob.gates._land_parity for real, fixing the reversed layering direction the T-3456 followup docstring called out. _land_cmd.py now imports these from frob.gates._land_parity instead of defining them; its own sys.exit(1) enforcing assertions are unchanged. No circular import: frob.gates no longer depends on frob.app.ticket_runner in either direction.

### Changed
```
 tickets/T-3467/ticket.md | 15 ++++++++++++++-
 1 file changed, 14 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_missing_both_directives_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_with_both_directives_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_no_diff_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_new_over_threshold_function_fires` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_pre_existing_over_threshold_function_merely_touched_is_quiet` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_no_diff_is_quiet` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_an_unrelated_land_touching_no_python_files_is_unaffected` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: 18 error(s), 4182 warning(s), 866 waived
- error-findings: AFFECT001@src/frob/gates/_land_parity.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC006@tickets/T-3411/ticket.md, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, LARGE001@.claude/hooks/root-write-guard.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PRE001@tickets/T-3467, REL001@src/frob/__init__.py, SELFAUDIT001@src/frob/gates/_land_parity.py, SELFAUDIT001@src/frob/gates/_policy_weakening_gate.py, SELFAUDIT001@tests/unit/strata/test_strata_core_gil.py, SELFAUDIT001@tests/unit/test_land_parity_gate.py, SELFAUDIT001@tests/unit/test_sync_claude_config_stale_guard_t3408.py, SELFAUDIT001@tests/unit/verify/test_worker.py, TICK004@tickets.md, WAIVE011@frob-ratchet.lock.json
