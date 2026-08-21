---
id: T-2776
title: 'Reformat batch 2/N: 10 files pending ruff-format (T-2359 child)'
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
- src/frob/_cli_parsers/_misc.py
- src/frob/_cli_parsers/_reporting.py
- src/frob/app/fmt_runner.py
- src/frob/app/ticket_runner/_land_cmd.py
- src/frob/dup/_pipeline/_fingerprint.py
- src/frob/dup/_template.py
- src/frob/gates/_coverage_sites.py
- src/frob/gates/_dead_symbols.py
- src/frob/gates/_docblocks.py
- src/frob/gates/_fix_engine.py
evidence_scope:
- tests/test_docblocks_gate.py
- tests/unit/test_land_auto_rebase.py
- tests/unit/test_land_cmd_backpressure.py
- tests/unit/test_land_cmd_quarantine.py
- tests/unit/test_land_finish_guard.py
- tests/unit/test_land_finish_idempotent.py
- tests/test_ticket_merge_driver.py
- tests/test_ticket_land.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/_cli_parsers/_misc.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/_cli_parsers/_reporting.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/fmt_runner.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/app/ticket_runner/_land_cmd.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/dup/_pipeline/_fingerprint.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/dup/_template.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_coverage_sites.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_dead_symbols.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_docblocks.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
- op: add
  glob: src/frob/gates/_fix_engine.py
  reason: batch 2 of T-2359 ruff-format reformat
  actor: logan
  at: '2026-08-21'
evidence:
- tests/test_docblocks_gate.py::TestPythonNamespace::test_python_import_of_nonexistent_symbol_is_stale
- tests/unit/test_land_auto_rebase.py::TestAutoSyncWorktreeOntoMain::test_merges_the_worktree_onto_the_new_main_tip
- tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure::test_dry_run_skips_the_check
- tests/unit/test_land_cmd_quarantine.py::TestQuarantineOverrideCeilings::test_not_quarantined_is_unchanged
- tests/unit/test_land_finish_guard.py::TestScanForLiveWorktreeProcess::test_finds_a_process_cwd_into_the_path
- tests/unit/test_land_finish_idempotent.py::TestTicketTerminalStateOnMain::test_done_ticket_returns_its_state
- tests/test_ticket_merge_driver.py::TestArchivedIdsForMergeDriver::test_not_mid_merge_falls_back_to_disk_based_archived_ids
- tests/test_ticket_land.py::TestFrobDirNeverLeaksIntoGitAdd::test_frob_scratch_files_are_gitignored_not_tracked
- tests/test_gates.py::TestFixEngineTierABatch2::test_fmt001_wraps_overlong_directive_line_and_reverifies_clean
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: a1d1e63f52cc6ee77a6fe307716031fe2c69e4e0
---
Batch 2/N of T-2359's ruff-format-only reformat. This child covers exactly
the 10 files listed in its scope. Filed as a child rather than landing
against T-2359 directly because `frob ticket land` closes its target
ticket, and T-2359's own acceptance criteria (zero files needing
reformat repo-wide) cannot honestly bind until every batch lands.