---
id: T-3665
title: 'win32: process-pool test hardcodes forkserver availability'
state: done
kind: bug
origin: human
created: '2026-09-01'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/gates_suite/test_run.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'BUG002 front door (T-2393): test-only fix: corrects a hardcoded POSIX-only
    assertion in an existing test to check the platform-appropriate property; product''s
    own _process_pool_start_method fallback logic was already correct and is unchanged'
  actor: logan
  at: '2026-09-01'
  old_length: 1974
  new_length: 2222
- mode: append
  reason: 'BUG002 front door (T-2393): test-only fix: corrects a hardcoded POSIX-only
    assertion in an existing test to check the platform-appropriate property; product''s
    own _process_pool_start_method fallback logic was already correct and is unchanged'
  actor: logan
  at: '2026-09-01'
  old_length: 2222
  new_length: 2470
evidence:
- tests/gates_suite/test_run.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available
- tests/gates_suite/test_run.py::TestProcessPoolGates::test_process_pool_start_method_falls_back_to_spawn_without_forkserver
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows CI run 33521416410 (tracked by T-3659): tests/gates_suite/test_run.py::TestProcessPoolGates::test_open_process_pool_preloads_forkserver_when_available fails on win32 only.

Traceback: `assert "forkserver" in multiprocessing.get_all_start_methods()` fails with `assert 'forkserver' in ['spawn']` -- CPython's multiprocessing module genuinely never registers a forkserver start method on win32 (it requires os.fork, which Windows does not have); this is not something product code can special-case around, it is a real platform capability difference.

Confirmed NOT a product bug: src/frob/gates/__init__.py's own `_process_pool_start_method()` already handles this correctly -- `if "forkserver" in multiprocessing.get_all_start_methods(): return "forkserver"` else falls back to `"spawn"`. The test itself calls this same function earlier (`expected_method = _process_pool_start_method()`) and correctly gates its forkserver-preload assertions behind `if expected_method == "forkserver":` -- but then has one FINAL, unconditional assertion at the end (`assert "forkserver" in multiprocessing.get_all_start_methods()`, line 459) that hard-codes the POSIX-only assumption the rest of the test already knows how to avoid.

Fix direction (test only, per campaign's fix-direction rule -- this is a test hardcoding a POSIX shape, not a product gap): drop the final unconditional assertion, or replace it with something that asserts the SAME conditional property the rest of the test already checks (e.g. assert the chosen a `expected_method in multiprocessing.get_all_start_methods()`, which is the property that actually matters and holds on every platform) -- never weaken any of the existing forkserver-preload assertions inside the `if expected_method == "forkserver":` block, those stay exactly as strict on a platform that does have it.

Traceback evidence: scratchpad/win-33521-failures.txt lines 16479-17593.

References T-3659 (tracking ticket for this campaign).


frob:no-behavior-change reason="test-only fix: corrects a hardcoded POSIX-only assertion in an existing test to check the platform-appropriate property; product's own _process_pool_start_method fallback logic was already correct and is unchanged"

frob:no-behavior-change reason="test-only fix: corrects a hardcoded POSIX-only assertion in an existing test to check the platform-appropriate property; product's own _process_pool_start_method fallback logic was already correct and is unchanged"