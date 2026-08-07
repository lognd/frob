---
id: T-0177
title: 'frob serve daemon: incremental gate evaluation over the warm obligation graph'
state: done
kind: feature
origin: human
created: '2026-07-18'
priority: medium
blocked_by:
- T-0410
parent: null
tier: ticket
sprint: null
scope:
- src/frob/serve/**
- src/frob/gates/**
- src/frob/graph/**
- src/frob/app/**
- pyproject.toml
- Makefile
- docs/modules/serve.md
- tickets.md
- tests/test_serve.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: remove
  glob: tests/**
  reason: 'scope hygiene (T-0455): narrow speculative tests/** to mirrored path'
  actor: logan
  at: '2026-07-20'
- op: add
  glob: tests/test_serve.py
  reason: T-0177 serve work maps to tests/test_serve.py
  actor: logan
  at: '2026-07-20'
evidence:
- tests/test_serve.py::TestBuildServer::test_registers_all_five_tools
- tests/test_serve.py::TestRepoDirtyKey::test_non_git_root_is_always_dirty
- tests/test_serve.py::TestRepoDirtyKey::test_clean_repo_key_is_stable_across_calls
- tests/test_serve.py::TestRepoDirtyKey::test_tracked_edit_changes_the_key
- tests/test_serve.py::TestRepoDirtyKey::test_untracked_file_content_edit_changes_the_key
- tests/test_serve.py::TestWarmState::test_second_call_is_cache_hit
- tests/test_serve.py::TestWarmState::test_file_change_forces_rebuild
- tests/test_serve.py::TestWarmState::test_invalidate_is_a_noop_when_nothing_cached
- tests/test_serve.py::test_warm_state_rebuilds_iff_tree_changed
- tests/test_serve.py::TestCheckDelta::test_delta_against_fresh_baseline_is_empty
- tests/test_serve.py::TestCheckDelta::test_missing_baseline_is_full_set
- tests/test_serve.py::TestCheckDelta::test_delta_reports_new_violation
- tests/test_serve.py::TestCheckDelta::test_verify_true_matches_when_no_drift
- tests/test_serve.py::TestRunTouchedTests::test_no_diff_selects_nothing
- tests/test_serve.py::TestRunTouchedTests::test_bad_base_is_git_failed
designated_repro_test: null
threat: null
component: null
---
frob serve is already a FastMCP stdio server with 5 read-only tools (doable tickets, stale docs, graph query, doc-for, check-scope) and is now wired into the coordinator's MCP config. Grow it into the structural fix for test-wait latency: the obligation graph knows exactly which obligations a diff can invalidate (frob test --base already proves the touched-set concept for tests) -- exploit it for gates. Deliverables: (1) warm state: the daemon holds the parsed graph snapshot, collected test ids, and the stamped violation baseline, refreshing incrementally on file-change (mtime/content-hash walk, reuse the .frob sqlite cache) instead of cold-parsing per invocation; (2) frob_check_delta MCP tool: given a base ref or dirty set, evaluate ONLY the obligations whose inputs changed and return the violation delta against the stamped baseline, in seconds; (3) frob_run_touched_tests tool wrapping the existing touched-set selection; (4) correctness guarantee: incremental results must provably match a cold frob check -- add a verification mode that runs both and diffs, plus property tests for the invalidation logic (an obligation NOT re-evaluated must have had no changed inputs -- vacuous-pass doctrine applies to the cache); (5) packaging: mcp becomes a proper [serve] extra in pyproject (mirroring [smt]) with _require_mcp's remedy message updated; Makefile install-tool already passes --with mcp -- reconcile with the extra; (6) docs/modules/serve.md updated with the daemon lifecycle and the staleness/correctness contract. Sequence AFTER the T-0148 sweep lands (gates code moves under it).