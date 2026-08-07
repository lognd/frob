---
id: T-1635
title: 'Residual intermittent test failures: same commit, one run red and the next
  green'
state: done
kind: bug
origin: human
created: '2026-08-06'
priority: high
parent: null
tier: ticket
sprint: null
scope:
- tests/**
- src/frob/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_gates_suppress.py::TestMypyOracleCacheDir::test_mypy_invocation_pins_cache_dir_under_root
- tests/test_serve_watch.py::TestWatchThread::test_change_fires_on_change_callback
- tests/test_serve_watch.py::TestWatchThread::test_stop_joins_promptly
- tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires
- tests/test_tickets_ledger_concurrency.py::TestArchiveRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_archive
- tests/test_tickets_ledger_concurrency.py::TestRenumberOneRaceWithConcurrentNew::test_concurrent_new_ticket_survives_a_racing_renumber_one
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds
- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_two_unmeasured_gate_claims_never_vacuously_match
- tests/test_registry_exhaustiveness.py::TestArchChecksReg008BurnDown::test_no_reg008_findings_for_arch_checks_yaml
- tests/test_registry_exhaustiveness.py::TestSystemDesignReg008BurnDown::test_no_reg008_findings_for_system_design_yaml
- tests/unit/test_conftest_stackdump.py::TestSelfScanHeavyGrouping::test_self_scan_heavy_tests_share_one_xdist_group
- tests/test_serve_socket.py::TestShutdownReapsChildren::test_frob_shutdown_exits_and_reaps_within_budget
designated_repro_test: null
threat: null
component: null
---
T-1596 fixed one real xdist polluter (the FROB_PARSE_ARTIFACT_CACHE env leak) and honestly reported a residual set it could not reproduce. T-1596 is now done, so that residual set is tracked nowhere. This ticket is its home.

Confirmed intermittent, 2026-08-06, two consecutive full runs on the SAME commit:
- run A: SUITE-RESULT exitstatus=1 collected=8564 failed=2 -- tests/test_ticket_land.py::TestClaimDivergencePostMerge::test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds FAILED
- run B: SUITE-RESULT exitstatus=0 collected=8564 failed=0 -- the same test passed
- in isolation: passes

(The other failure in run A was environment -- an orphaned land.lock, T-1634 -- not this class.)

Previously observed in the same family, each passing in isolation: TestMapRunner (both), TestOutlineRunner::test_directory_target_falls_back_to_map, tests/test_lang.py::TestParseCache::test_second_call_same_content_is_a_hit, TestSetDoneReportClaims, TestLedgerV2LandMergeStory, TestReverifyCli, TestNewFileCarveOut.

Why this must not be dismissed as "flaky": an intermittent failure trains everyone -- human and agent -- to re-run and move on. That habit is what let genuinely broken things hide behind dismissed reds for most of this drive (the ledger-v2 auto-commit no-op and the invisible Done reports both survived inside noise). A suite whose verdict is probabilistic is only marginally better than one that truncates silently, which is the problem T-1596's SUITE-RESULT hook just fixed.

Approach:
1. Make it reproducible before trying to fix it. Capture the failing worker's full test order (`-p no:randomly` plus the xdist worker assignment, or run with a fixed seed and `--dist=loadgroup` as configured) and replay that exact order. An unreproducible fix is unverifiable.
2. Suspect shared process state first, since every member passes alone: module-level caches, monkeypatched globals left unrestored, cwd, env vars, and `.frob/` derived state (cache.db, gate-cache.db, derived.lock, coverage stamps). tests/conftest.py already carries autouse resets for the parse cache (T-0926), color env (T-1586), and the parse-artifact-cache env (T-1591) -- this is the same shape, one layer deeper.
3. Fix at the source with an autouse reset. Do NOT fix by reordering, serializing, or marking xfail. If a piece of state is genuinely un-resettable, say so explicitly and explain why.
4. Add the ordering as a regression test where practical, so the polluter cannot silently return.

Acceptance: ten consecutive full-suite runs, each verified via its SUITE-RESULT line, all reporting failed=0.