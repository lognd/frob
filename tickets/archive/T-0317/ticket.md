---
id: T-0317
title: test collector must honor per-tree [[test.runner]] cwd/project when COLLECTING,
  not just running
state: done
kind: feature
origin: auditor
created: '2026-07-19'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/testing/**
- tests/**
- docs/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_testing.py::TestCollectPythonTestsNestedRunner::test_nested_test_runner_cwd_is_collected_and_rerooted
- tests/test_testing.py::TestCollectPythonTestsNestedRunner::test_missing_nested_runner_dir_degrades_to_empty_not_err
- tests/test_testing.py::TestCollectPythonTests::test_parses_node_ids_and_caches_on_content_hash
designated_repro_test: null
threat: null
component: null
---
FROBLEMS (aprog-public): frob's test collector runs in the OUTER repo environment, so frob:tests evidence ids inside a nested project (slidegen/tests, imports pptx/PIL) cannot be collected -- collection fails there and the binding is unresolvable, forcing an outer-repo proxy test as evidence. frob.toml [[test.runner]] already exists and honors cwd/project when RUNNING; the collector must honor it when COLLECTING too (run pytest --collect-only in each runner's cwd/venv and union the node ids). Enables real evidence for nested-project tests. Test: a [[test.runner]] pointed at a nested project collects that project's node ids.