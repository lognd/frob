---
id: T-3341
title: fix FROB_VERBOSE env leak in TestVerboseFlag (test isolation)
state: done
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
body_changes:
- mode: append
  reason: designated repro is order-dependent and cannot be proven via a single-node-id
    BUG002 check; follow-up filed to widen the repro-check contract
  actor: logan
  at: '2026-08-29'
  old_length: 986
  new_length: 1675
- mode: append
  reason: designated repro is order-dependent and cannot be proven via a single-node-id
    BUG002 check; follow-up filed to widen the repro-check contract
  actor: logan
  at: '2026-08-29'
  old_length: 1675
  new_length: 2364
evidence:
- tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_v_sets_debug_env_var
- tests/unit/test_main_entry.py::TestVerboseFlag::test_dash_dash_verbose_sets_debug_env_var
- tests/unit/test_parse.py::TestParseCliPytest::test_json_output
- tests/unit/test_parse.py::TestParseCliTy::test_json_output
- tests/unit/test_parse.py::TestParseCliClang::test_json_output
- tests/unit/test_parse.py::TestParseCliJunit::test_json_output
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TestVerboseFlag.test_dash_v_sets_debug_env_var and test_dash_dash_verbose_sets_debug_env_var call monkeypatch.delenv('FROB_VERBOSE', raising=False) on an already-absent key -- pytest's monkeypatch does not register an undo action for a delenv on a key that was not present, so the SUT's direct os.environ['FROB_VERBOSE']='1' write later in the test is never reverted at teardown. This leaks FROB_VERBOSE=1 into the worker process for the rest of the pytest session, corrupting every later subprocess-based test that asserts on frob CLI stdout (confirmed root cause of tests/unit/test_parse.py's 4 test_json_output failures under full-suite/xdist runs -- DEBUG-level doctor.native-extension log lines leak onto stdout ahead of the JSON payload once FROB_VERBOSE=1 raises the stdout handler back to DEBUG). Fix: explicitly clean up the leaked env var after invoking the SUT in both tests (assert then monkeypatch.delenv again now that the value exists, so pytest registers a proper undo).

frob:waive BUG002 reason="order-dependent test-isolation leak (FROB_VERBOSE surviving teardown across pytest tests) -- the designated repro test passes in isolation both before and after the fix, and only fails when run in the specific multi-test sequence that reproduces the leak; BUG002 checks a single node id in isolation so it cannot distinguish never-reproduces-alone from fixed for this bug class. Underlying code fix independently hand-verified (see done report): the leak reproduces at parent (be9e76738cc90171b3fe7f87f547af94e98d5b6b) and is gone after the fix when running tests/unit/test_main_entry.py::TestVerboseFlag + tests/unit/test_parse.py together." follow_up="T-3352"

frob:waive BUG002 reason="order-dependent test-isolation leak (FROB_VERBOSE surviving teardown across pytest tests) -- the designated repro test passes in isolation both before and after the fix, and only fails when run in the specific multi-test sequence that reproduces the leak; BUG002 checks a single node id in isolation so it cannot distinguish never-reproduces-alone from fixed for this bug class. Underlying code fix independently hand-verified (see done report): the leak reproduces at parent (be9e76738cc90171b3fe7f87f547af94e98d5b6b) and is gone after the fix when running tests/unit/test_main_entry.py::TestVerboseFlag + tests/unit/test_parse.py together." follow_up="T-3352"