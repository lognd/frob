---
id: T-3341
title: fix FROB_VERBOSE env leak in TestVerboseFlag (test isolation)
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
- tests/unit/test_main_entry.py
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
TestVerboseFlag.test_dash_v_sets_debug_env_var and test_dash_dash_verbose_sets_debug_env_var call monkeypatch.delenv('FROB_VERBOSE', raising=False) on an already-absent key -- pytest's monkeypatch does not register an undo action for a delenv on a key that was not present, so the SUT's direct os.environ['FROB_VERBOSE']='1' write later in the test is never reverted at teardown. This leaks FROB_VERBOSE=1 into the worker process for the rest of the pytest session, corrupting every later subprocess-based test that asserts on frob CLI stdout (confirmed root cause of tests/unit/test_parse.py's 4 test_json_output failures under full-suite/xdist runs -- DEBUG-level doctor.native-extension log lines leak onto stdout ahead of the JSON payload once FROB_VERBOSE=1 raises the stdout handler back to DEBUG). Fix: explicitly clean up the leaked env var after invoking the SUT in both tests (assert then monkeypatch.delenv again now that the value exists, so pytest registers a proper undo).