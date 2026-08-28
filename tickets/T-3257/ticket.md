---
id: T-3257
title: AppConfig(command=...) unknown-argument ty finding, unrelated to platform work
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/unit/test_app_runners_process.py
- tests/unit/test_pytest_spawn_env_wiring.py
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
Found while working T-3244: ty (any --python-platform target, including the default host platform) reports error[unknown-argument]: Argument 'command' does not match any known parameter at several AppConfig(command=...) call sites in these two test files (test_app_runners_process.py:60,74,90,99,112; test_pytest_spawn_env_wiring.py:182,223,256). Reproduces identically with a bare 'uv run ty check <file>' (no --python-platform flag), so this is NOT one of T-3244's platform-unsafe findings -- a different, pre-existing bug shape (AppConfig's actual constructor signature vs. what these tests pass) left untouched by T-3244's scope. Needs its own triage: either AppConfig genuinely dropped/renamed a 'command' field these tests still pass positionally as a kwarg, or these call sites need updating to whatever the current field is.