---
id: T-3257
title: AppConfig(command=...) unknown-argument ty finding, unrelated to platform work
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
- tests/unit/test_app_runners_process.py
- tests/unit/test_pytest_spawn_env_wiring.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: BUG002 flags the bound evidence as confirmatory-only because it passes at
    the parent commit too -- correct, since this is a static ty finding with no runtime
    behavior change, not a test-detectable regression
  actor: logan
  at: '2026-08-29'
  old_length: 832
  new_length: 1453
evidence:
- tests/unit/test_app_runners_process.py::TestOpsRunnerProcessDelegation::test_process_subcommand_delegates_to_process_runner
- tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_reports_reaped_pids
- tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_reports_nothing_reaped
- tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_reap_json_mode_emits_json
- tests/unit/test_app_runners_process.py::TestProcessRunnerReap::test_unknown_process_subcommand_exits_1
- tests/unit/test_pytest_spawn_env_wiring.py::TestMutateRunnerWiring::test_must_fire_applies_and_warns_before_run_mutations
- tests/unit/test_pytest_spawn_env_wiring.py::TestPerfRunnerProfileWiring::test_must_fire_applies_and_warns_for_tests_path
- tests/unit/test_pytest_spawn_env_wiring.py::TestPerfRunnerProfileWiring::test_must_stay_quiet_raw_argv_path_does_not_wire
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: f076963450747bda9536928670888d5389526c15
---
Found while working T-3244: ty (any --python-platform target, including the default host platform) reports error[unknown-argument]: Argument 'command' does not match any known parameter at several AppConfig(command=...) call sites in these two test files (test_app_runners_process.py:60,74,90,99,112; test_pytest_spawn_env_wiring.py:182,223,256). Reproduces identically with a bare 'uv run ty check <file>' (no --python-platform flag), so this is NOT one of T-3244's platform-unsafe findings -- a different, pre-existing bug shape (AppConfig's actual constructor signature vs. what these tests pass) left untouched by T-3244's scope. Needs its own triage: either AppConfig genuinely dropped/renamed a 'command' field these tests still pass positionally as a kwarg, or these call sites need updating to whatever the current field is.

frob:waive BUG002 reason="ty-only static type-check defect (unknown-argument on AppConfig(command=...)); AppConfig is a pydantic BaseModel with default extra-field handling so the bogus kwarg was silently ignored at runtime both before and after the fix -- no runtime behavior changed, so no pytest evidence can fail-then-pass across this fix by construction. The 24 ty findings (8 sites x 3 platforms) are the actual reproduction, verified via uv run ty check --python-platform {linux,win32,darwin} src tests/unit/test_app_runners_process.py tests/unit/test_pytest_spawn_env_wiring.py: unknown-argument count 24 -> 0."