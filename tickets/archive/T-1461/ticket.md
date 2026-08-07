---
id: T-1461
title: clear T-1454/T-1456 land residue
state: done
kind: bug
origin: human
created: '2026-08-02'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/gates/__init__.py
- src/frob/serve/_tools.py
- tests/test_ticket_work_and_land_finish.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_ticket_work_and_land_finish.py::TestDefaultWorkWorktree::test_slug_is_lowercased_ticket_id_under_dot_claude_worktrees
- tests/test_ticket_work_and_land_finish.py::TestWork::test_creates_worktree_merges_main_and_starts_ticket
- tests/test_ticket_work_and_land_finish.py::TestWork::test_reuses_an_existing_worktree_and_merges_main_for_freshness
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_fmt_half_canonicalizes_a_non_canonical_directive
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_out_of_scope_file_with_noncanonical_directive_is_left_untouched
- tests/test_ticket_work_and_land_finish.py::TestAbsorbPreLandFixes::test_in_scope_file_with_noncanonical_directive_is_still_fixed
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_no_new_error_is_a_silent_no_op
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_fixed_by_tier_a_lands_with_a_followup_commit
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_new_error_absent_before_land_refuses_and_reverts
- tests/test_ticket_work_and_land_finish.py::TestPostLandUnscopedSweep::test_unmeasurable_baseline_or_fresh_skips_the_sweep
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_proof_verifies_a_real_land
- tests/test_ticket_work_and_land_finish.py::TestLandProofAndFinish::test_finish_removes_the_worktree
- tests/test_gate_cache.py::TestTrackedSnapshot::test_symbol_iteration_records_file
- tests/test_gate_cache.py::TestTrackedSnapshot::test_getitem_records_only_accessed_key
- tests/test_gate_cache.py::TestTrackedSnapshot::test_file_hashes
- tests/test_gate_cache.py::TestExtraKey::test_extra_key
- tests/test_gate_cache.py::TestSideChannelKey::test_model_side_channel_key_changes_on_field_edit
- tests/test_gate_cache.py::TestSideChannelKey::test_model_side_channel_key_stable_for_equal_content
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_miss_then_hit_skips_second_call
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_edit_to_untouched_file_stays_a_hit
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_edit_to_touched_file_forces_miss
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_new_untouched_file_forces_miss_membership_guard
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_extra_change_forces_miss
- tests/test_gate_cache.py::TestEvaluateCacheableGate::test_invalidate_forces_next_call_to_miss
- tests/test_gate_cache.py::TestRunGatesUseCache::test_use_cache_false_is_default_and_unaffected
- tests/test_gate_cache.py::TestRunGatesUseCache::test_use_cache_true_produces_identical_report_to_cold
- tests/test_gate_cache.py::TestRunGatesUseCache::test_ack_invalidates_cached_drift001
- tests/test_gate_cache.py::TestColdDiffOracle::test_cache_agrees_with_cold_across_random_edits
designated_repro_test: null
threat: null
component: null
---
T-1454/T-1456 landed a post-land unscoped error sweep in _land_cmd.py plus
gate-cache side-channel work in gates/__init__.py, leaving 13 gate errors
as residue on main:

- src/frob/app/ticket_runner/_land_cmd.py: 3x E501 (lines ~320/346/429),
  ARCH001 on _post_land_unscoped_error_sweep (114 lines, threshold 60),
  ARCH001+ARCH103 on _land (142 lines, threshold 60; also mixes I/O,
  string-formatting, and 10 decision points)
- src/frob/gates/__init__.py: ARCH001 on _cacheable_gate_call (63 lines,
  threshold 60); also an I001 unsorted-import warning at line 49
- src/frob/serve/_tools.py: I001 unsorted-import warning at line 395
- tests/test_ticket_work_and_land_finish.py: 6x OPAQUE001 setattr-monkeypatch
  findings needing a file-level waiver per the
  tests/unit/test_ticket_close_bug002_t1438.py precedent

Plan: split _post_land_unscoped_error_sweep's baseline-capture /
delta-compare / autofix-retry / refuse-revert phases into private helpers;
extract _land's sweep orchestration (and any other coherent phase) into a
helper, preserving behavior exactly (all 12 tests in
tests/test_ticket_work_and_land_finish.py must stay green); extract
_cacheable_gate_call's side-channel key assembly per-gate mapping into a
helper/table; add the file-level frob:waive OPAQUE001 directive to
tests/test_ticket_work_and_land_finish.py; fix the I001 import-sort issues;
run uv run ruff format on everything touched.