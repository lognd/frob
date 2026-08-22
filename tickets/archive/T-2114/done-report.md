## Done report

Changed:
- src/frob/app/ticket_runner/_land_cmd.py
  - `_assert_new_public_symbols_have_doc_and_test_edge_pre_land` (new)
  - wired into land's pre-merge prepare sequence, all profiles

Evidence:
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_cli_land_end_to_end_refuses_a_worktree_with_a_new_undocumented_symbol
  (designated BUG002 repro, confirmed FAILED_AT_PARENT against 9136ff534,
  the commit where the test exists but the fix does not)
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_empty_touched_set_is_a_no_op

Full file re-run: tests/test_ticket_work_and_land_finish.py -- 54 passed,
5 failed (TestLandProofAndFinish -- pre-existing, unrelated, filed as
T-2167).

Filed: none

Gates: frob check --ticket T-2114 clean (recovery agent re-verification)
