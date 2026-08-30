---
id: T-3467
title: Move T-2114/ARCH001-diff pure logic into frob.gates._land_parity for real (fix
  the layering direction)
state: in-progress
kind: feature
origin: human
created: '2026-08-30'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_missing_both_directives_fires
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_new_public_symbol_with_both_directives_is_quiet
- tests/unit/test_land_parity_gate.py::TestLandParityDocTestGate::test_no_diff_is_quiet
- tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_new_over_threshold_function_fires
- tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_pre_existing_over_threshold_function_merely_touched_is_quiet
- tests/unit/test_land_parity_gate.py::TestLandParityLongFunctionGate::test_no_diff_is_quiet
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_no_edges_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_a_new_public_symbol_with_both_edges_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertNewPublicSymbolsHaveDocAndTestEdges::test_an_unrelated_land_touching_no_new_public_symbols_is_unaffected
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_new_over_threshold_function_refuses_the_land
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_a_pre_existing_over_threshold_function_merely_touched_does_not_refuse
- tests/test_ticket_work_and_land_finish.py::TestAssertDiffDoesNotWorsenLongFunctions::test_an_unrelated_land_touching_no_python_files_is_unaffected
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-3456. frob.gates._land_parity (LANDPARITY001/LANDPARITY002) currently imports its pure logic (_new_public_symbols_missing_doc_or_test_edge, _new_or_worsened_long_functions_in_diff, and their shared helpers _is_generated_or_test_path/_public_top_level_defs/_frob_directive_block/_DOC_TEST_EDGE_FAMILIES) FROM frob.app.ticket_runner._land_cmd (deferred, call-time only, to dodge a real circular-import risk) rather than the reverse -- the ticket body's own suggested end state. This was a scheduling-only workaround: _land_cmd.py was under an exclusive scope lease held by a concurrent ticket (T-2642) for T-3456's entire session, so genuinely MOVING the functions out of it was not available. [arch.layering] (frob.toml) is declared but not wired into frob check yet (T-0620), so the current gates -> app.ticket_runner import direction trips no live enforcement today, but is still backwards long-term. Once _land_cmd.py's lease is free: move the named functions into frob.gates._land_parity for real, update _land_cmd.py to import them back (its own _assert_new_public_symbols_have_doc_and_test_edge_pre_land/_assert_diff_does_not_worsen_long_functions_pre_land stay the enforcing sys.exit(1) call sites, unchanged behavior), and delete the now-duplicate copies. Also note: the T-2280 file-local-error diff-scoped check in the same file shares _is_generated_or_test_path/_frob_directive_block -- update that import site too when moving.