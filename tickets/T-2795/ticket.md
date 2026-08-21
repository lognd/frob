---
id: T-2795
title: 'Reformat batch 10/N: 13 files pending ruff-format (T-2359 child)'
state: done
kind: feature
origin: human
created: '2026-08-21'
priority: medium
parent: T-2359
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_land_already_landed.py
- tests/unit/test_land_cmd_backpressure.py
- tests/unit/test_land_cmd_drain_wiring.py
- tests/unit/test_land_cross_ticket_leakage.py
- tests/unit/test_land_duplicate_ticket_id.py
- tests/unit/test_land_machinery_owned_leakage.py
- tests/unit/test_land_root_resolution.py
- tests/unit/test_land_sibling_regression.py
- tests/unit/test_land_squash_residue_reclaim.py
- tests/unit/test_scaffold_project_e501_t2596.py
- tests/unit/test_scope_closure_warning_collapse_t1556.py
- tests/unit/test_t2450_scope_repair.py
- tests/unit/test_ticket_2691_doc006.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/test_land_already_landed.py::TestAlreadyLandedOnMain::test_refuses_with_a_diagnostic_message_when_scope_diff_is_empty
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check
- tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring::test_real_rapid_land_spawns_both_sweep_and_drain
- tests/unit/test_land_cross_ticket_leakage.py::TestCrossTicketLeakage::test_refuses_when_sibling_ticket_still_open
- tests/unit/test_land_duplicate_ticket_id.py::TestDetectDuplicateTicketIdCollisions::test_flags_id_with_genuinely_different_content_on_both_sides
- tests/unit/test_land_machinery_owned_leakage.py::TestMachineryOwnedLeakageExemption::test_rapid_debt_append_never_leaks_even_when_a_sibling_declares_it
- tests/unit/test_land_root_resolution.py::TestRootResolvesToADifferentWorktree::test_refuses_when_root_is_a_different_registered_worktree
- tests/unit/test_land_sibling_regression.py::TestSiblingStateRegressionGuard::test_no_regression_when_sibling_state_only_improves_or_holds
- tests/unit/test_land_squash_residue_reclaim.py::TestReclaimOrphanedSquashResidue::test_reclaims_when_no_live_land_holds_the_lock
- tests/unit/test_scaffold_project_e501_t2596.py::TestScaffoldProjectLineLength::test_no_unexempted_long_lines
- tests/unit/test_scope_closure_warning_collapse_t1556.py::TestEmitScopeClosureWarnings::test_no_warnings_logs_nothing
- tests/unit/test_t2450_scope_repair.py::TestT2450ScopeRepair::test_no_scope_entry_contains_a_semicolon
- tests/unit/test_ticket_2691_doc006.py::TestTicket2691Doc006Regression::test_backticked_future_verb_is_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 165e79c78a339f8444b777def7b6bf7efb867ddd
---
Batch 10/N of T-2359: apply ruff-format-only reformat to 13
independent unit test files (land machinery tests + misc). No
semantic changes; format-only diff.