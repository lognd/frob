---
id: T-0600
title: 'frob-exports triage: src/frob/gates, src/frob/graph, src/frob/process/parsers,
  src/frob/registry (14 symbols across 4 packages)'
state: done
kind: bug
origin: agent
created: '2026-07-22'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/graph/**
- src/frob/process/parsers/**
- src/frob/registry/**
- tests/test_graph.py
- docs/modules/graph.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: tests/test_graph.py
  reason: 'T-0600''s per-symbol export/demote decision for src/frob/graph/cache.py''s
    get_file_hash (demoted to _get_file_hash, no external consumer) touches its only
    test module and the doc anchor list naming it.

    '
  actor: logan
  at: '2026-07-23'
- op: add
  glob: docs/modules/graph.md
  reason: 'T-0600''s per-symbol export/demote decision for src/frob/graph/cache.py''s
    get_file_hash (demoted to _get_file_hash, no external consumer) touches its only
    test module and the doc anchor list naming it.

    '
  actor: logan
  at: '2026-07-23'
evidence:
- tests/test_graph.py::TestCacheModule::test_store_and_load_file_data_roundtrip
- tests/test_gates_fmt_directives.py::TestCrlfPreservation::test_format_paths_preserves_crlf_end_to_end
- tests/test_gates_ratchet.py::TestSnapshotRatchet::test_writes_committed_lock_file
- tests/unit/graph/test_dsl.py::TestFoldCommentRuns::test_single_line_run_has_count_one
- tests/test_registry_staleness.py::TestMissingGateRuleIds::test_finds_rules_with_no_entry
- tests/unit/test_process_guard.py::TestCheckStagesHonorExecKillSwitch::test_run_ruff_disabled
- tests/test_graph.py::TestCacheModule::test_schema_version_mismatch_wipes_derived_rows
designated_repro_test: null
threat: null
component: null
---
frob-exports currently reports (measured 2026-07-22): src/frob/gates 9 public symbols missing from __init__.py, src/frob/graph 2, src/frob/process/parsers 1, src/frob/registry 2 (14 total). For each symbol, decide per-symbol: export it from the package's __init__.py, or demote it to private (leading underscore) if it should not be public API. No blanket waiver -- each symbol gets an explicit decision. Acceptance: frob-exports(src/frob/gates), frob-exports(src/frob/graph), frob-exports(src/frob/process/parsers), frob-exports(src/frob/registry) summary lines report 0 unresolved findings (exported, demoted, or waived-with-reason), no threshold loosened without a disclosed decision.