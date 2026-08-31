---
id: T-3556
title: TestAutofixManifest must-fire is CI-flaky
state: queued
kind: bug
origin: human
created: '2026-08-31'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_gates.py
- src/frob/gates/_fix_engine_shared.py
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
MEASURED run 33361224273 (HEAD 8d4c18055): tests/test_gates.py::TestAutofixManifest::test_killed_mid_handler_leaves_manifest_naming_completed_fixes fails assert not True on BOTH ubuntu and macOS in CI, but presumably passed locally at T-3526's own land. This is a new must-fire test for the T-1348 autofix journal/manifest -- an environment-sensitive assertion (likely a race between the SIGKILL and the journal write, or a tmp-path shape difference under CI's parallelism). Reproduce with CI-like conditions (run it repeatedly, e.g. 10x under -n 4 locally) to find the race window, then make it deterministic using the T-3471 pattern (hold the state open until the expected condition is actually observed, rather than a fixed sleep/timing assumption) -- never weaken the property being tested.