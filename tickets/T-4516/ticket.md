---
id: T-4516
title: 'Test evidence: NUnit + Unity Test Framework collection and runners'
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
blocked_by:
- T-4518
parent: T-4513
tier: story
sprint: null
runs_last: false
milestone: 0.533.0
points: 1
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_collect_csharp.py
- src/frob/testing/_runners.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: v0.533.0
  new_value: v0.534.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: points
  old_value: null
  new_value: '1'
  reason: ticket sizing
  actor: logan
  at: '2026-09-22'
evidence:
- tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collects_test_and_unitytest
- tests/test_testing.py::TestCollectCsharpTests::test_collect_csharp_tests_collapses_parameterized_test_case
- tests/unit/test_dotnet_runner.py::TestRunDotnetTests::test_maps_passing_and_failing_ids
- tests/unit/test_dotnet_runner.py::TestRunDotnetTests::test_crash_with_no_results_file_is_run_failed
- tests/unit/test_unity_batchmode.py::TestParseUnityBatchmodeXml::test_parses_nested_test_suites_into_fqn_result_map
- tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode::test_crash_with_no_results_file_is_run_failed_distinct_from_a_test_failure
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-4516
branch: t-4516
---
Story: collect and run C#/Unity tests as evidence bindable by frob:tests directives. Parent for the two leaves below. blocked_by T-4518 because the Unity-vs-plain-C# distinction (asmdef, test assembly) needs project-model detection to route correctly.