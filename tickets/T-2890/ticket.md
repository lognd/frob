---
id: T-2890
title: test_check_delta_gates_only_json_daemon_matches_in_process flaky under xdist
state: queued
kind: bug
origin: human
created: '2026-08-22'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/test_app_daemon_proxy.py
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
Found while verifying T-2884: TestDifferentialParity.test_check_delta_gates_only_json_daemon_matches_in_process fails ~3/4 runs even on unmodified main HEAD when run under pytest-xdist (passes reliably with -p no:xdist). Likely gate-replay (T-2585, frob.gates._gate_cache.load_gate_run_replay/store_gate_run_replay) racing with a sibling xdist worker's own gate cache activity, or an unaccounted REPLAY marker not covered by _normalize_gate_timing. Verified: reverted src/frob/app/_daemon_proxy.py, src/frob/serve/_socketd.py, tests/test_app_daemon_proxy.py to HEAD content and re-ran the single test 3x under xdist -- failed 3/3, so this is not a T-2884 regression.