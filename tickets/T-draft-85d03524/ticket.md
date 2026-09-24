---
id: T-draft-85d03524
title: 'Windows-only: dotnet/unity runner tests fail with RunFailed (toolchain/env?)'
state: queued
kind: bug
origin: agent
created: '2026-09-24'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while draining CI run 35951365410 (dev 9e0c89bb19), windows-latest job
only. 4 failing node ids:
- tests/unit/test_dotnet_runner.py::TestRunDotnetTests::test_maps_passing_and_failing_ids
- tests/unit/test_dotnet_runner.py::TestRunDotnetTests::test_requested_id_missing_from_results_is_err
- tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode::test_maps_passing_and_failing_ids
- tests/unit/test_unity_batchmode.py::TestRunUnityBatchmode::test_requested_id_missing_from_results_is_err

All four fail with Err(...RunFailed)/Err(...RunFailed) where the test
expects Ok -- the dotnet/unity runner subprocess itself failed under the
test, not a mapping/parsing bug in the code under test. This LOOKS like a
missing/misconfigured dotnet or Unity toolchain on the windows-latest CI
runner image rather than a code regression -- needs confirmation by
reading the actual captured subprocess stderr (not visible in the
SUITE-RESULT-FAILED short summary this drain pass extracted) before
deciding whether this is a CI image/environment ticket or a real runner
bug. Also relevant: these two files' waivers are the exact ones cluster J
(WIRE002, see the sibling ticket for that cluster) found pointing at
already-done follow-up tickets -- may be related infrastructure drift in
the same two files.
