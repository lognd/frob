---
id: T-0599
title: 'frob-exports triage: src/frob, src/frob/app, src/frob/check (19 symbols across
  3 packages)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/__init__.py
- src/frob/app/**
- src/frob/check/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- tests/unit/test_config.py::test_stale_install_warning_flags_version_mismatch
- tests/unit/test_config.py::test_missing_toml_defaults
- tests/test_excludes.py::test_walk_pruned_does_not_descend_venv_or_git
- tests/test_excludes.py::test_iter_files_git_fast_path_matches_ls_files
- tests/test_gitio.py::TestSpawnRecorder::test_tallies_spawns_made_inside_the_block
- tests/test_gitio.py::TestGitCommonDir::test_resolves_absolute_common_dir
- tests/unit/test_memo.py::test_reset_run_memo_activates_an_unbounded_scope
- tests/unit/test_memo.py::test_run_memo_scope_deactivates_on_exit
- tests/unit/test_check.py::TestRunCheck::test_all_stages_skipped_returns_empty_result_for_root
designated_repro_test: null
threat: null
component: null
---
frob-exports currently reports (measured 2026-07-22): src/frob 5 public symbols missing from __init__.py, src/frob/app 11, src/frob/check 3 (19 total). For each symbol, decide per-symbol: export it from the package's __init__.py, or demote it to private (leading underscore) if it should not be public API. No blanket waiver -- each symbol gets an explicit decision. Acceptance: frob-exports(src/frob), frob-exports(src/frob/app), frob-exports(src/frob/check) summary lines report 0 unresolved findings (exported, demoted, or waived-with-reason), no threshold loosened without a disclosed decision.