## Done report

Changed:
tests/unit/test_land_already_landed.py
tests/unit/test_land_cmd_backpressure.py
tests/unit/test_land_cmd_drain_wiring.py
tests/unit/test_land_cross_ticket_leakage.py
tests/unit/test_land_duplicate_ticket_id.py
tests/unit/test_land_machinery_owned_leakage.py
tests/unit/test_land_root_resolution.py
tests/unit/test_land_sibling_regression.py
tests/unit/test_land_squash_residue_reclaim.py
tests/unit/test_scaffold_project_e501_t2596.py
tests/unit/test_scope_closure_warning_collapse_t1556.py
tests/unit/test_t2450_scope_repair.py
tests/unit/test_ticket_2691_doc006.py

Evidence: 13 pytest node ids bound, one per touched file, all pass.
Full-batch run: 75 collected, 0 failed.

Filed: this is child batch 10 of T-2359 (the parent reformat epic-tracking
ticket, still open pending further batches).

Gates: frob format applied ruff-check-fix (test_land_duplicate_ticket_id.py,
test_land_sibling_regression.py, test_t2450_scope_repair.py each picked
up an import-wrap fix) + ruff-format-write per file; diff reviewed by
hand, format-only (import-wrap/line-wrap), no semantic changes.

### Changed
```
 tickets/T-2795/ticket.md | 57 ++++++++++++++++++++++++++++++++++++++
 1 file changed, 57 insertions(+)
```

### Evidence
- `tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption::test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree::test_refuses_when_root_is_a_different_registered_worktree` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_no_regression_when_sibling_state_only_improves_or_holds` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock` (pytest node id, verified passing when recorded)
- `tests/unit/test_scaffold_project_e501_t2596.py::TestScaffoldProjectLineLength::test_no_unexempted_long_lines` (pytest node id, verified passing when recorded)
- `tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_no_warnings_logs_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_no_scope_entry_contains_a_semicolon` (pytest node id, verified passing when recorded)
- `tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 13 passed (from 13 evidence id(s))
- gates: 19 error(s), 1144 warning(s), 713 waived
- error-findings: CLAUDE001@.claude/hooks/sync-claude-config.py, COV001@src/frob/graph/callgraph.py, COV003@tickets/T-1688, COV003@tickets/T-2365, CYCLE001@src/frob/__init__.py, DOC006@docs/audits/test005-zero-classification-t1418.md, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/tickets/__init__.py, DRIFT002@docs/modules/tickets-data-storage.md, DUP001@tests/unit/test_land_sibling_regression.py, PERF004@src/frob/tickets/_evidence.py, REG002@docs/design/registry/check-coverage.yaml, SEC110@src/frob/app/ticket_runner/_verify.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SYS003@src/frob/check/__init__.py, TEST001@src/frob/strata/_multifile.py, TICK003@tickets.md, TICK004@tickets.md
