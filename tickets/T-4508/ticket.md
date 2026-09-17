---
id: T-4508
title: 'Evidence channel: dotnet test runner + Unity batchmode XML results parser'
state: in-progress
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4516
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/testing/_runners.py
- src/frob/testing/_unity_batchmode.py
- tests/unit/test_dotnet_runner.py
- tests/unit/test_unity_batchmode.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/unit/test_dotnet_runner.py
  reason: unit tests for run_dotnet_tests/TRX parsing
  actor: logan
  at: '2026-09-17'
- op: add
  glob: tests/unit/test_unity_batchmode.py
  reason: unit tests for unity batchmode parser/runner
  actor: logan
  at: '2026-09-17'
- op: add
  glob: docs/modules/testing.md
  reason: frob:doc target for run_dotnet_tests public api
  actor: logan
  at: '2026-09-17'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add an evidence-running channel that invokes 'dotnet test' for plain C# projects and documents/parses the Unity batchmode runner ('Unity -batchmode -runTests -testResults <path>') XML results into frob's evidence model. blocked_by T-4517 (node ids must exist before evidence can bind results to them).

GIVEN a plain C# test project (no Unity), WHEN the evidence channel runs, THEN it invokes 'dotnet test' and maps pass/fail results back to the collected node ids.
GIVEN a Unity batchmode XML results file (NUnit3 XML format), WHEN the parser runs on it, THEN it extracts per-test pass/fail/skip status keyed to the same node ids [UnityTest]/[Test] collection produced.
GIVEN a Unity batchmode run that exits non-zero (editor crash, license failure), WHEN the evidence channel handles it, THEN it surfaces a clear error distinct from a genuine test failure, not a silent empty-results false pass.

## Unblock log
- 2026-09-17: unblocked by T-4517 -- landed bcd55a738
