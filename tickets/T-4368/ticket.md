---
id: T-4368
title: macOS CI direct-interpreter test step never puts .venv/bin on PATH, so shutil.which(ty/mypy)
  reports unavailable
state: in-progress
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- .github/workflows/ci.yml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/test_ci_workflow_matrix.py::TestMacosTestStepPutsVenvBinOnPath::test_macos_test_step_run_script_prepends_venv_bin_to_path
designated_repro_test: null
evidence_changes:
- old_node: tests/test_ci_workflow_matrix.py::TestSelfGateRunsOnWindowsEvenIfTestStepFails::test_self_gate_step_runs_on_windows_after_a_prior_failure
  new_node: ''
  reason: wrong test bound initially -- unrelated to T-4368's PATH-export fix; replaced
    with the genuine regression test for this fix
  actor: logan
  at: '2026-09-09'
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
MEASURED, reproduced locally on linux by simulating the exact macOS CI invocation shape. macOS CI's Test step (.github/workflows/ci.yml, around line 370) runs the suite via .venv/bin/python -m pytest -q (direct interpreter path, T-4274's fix for pid-capture), unlike ubuntu's step which uses uv run pytest -q. uv run activates the target project's environment (prepending its bin dir to PATH) before exec'ing the child; direct .venv/bin/python invocation does not -- PATH is whatever the runner's ambient shell already has, which does not include this repo's own .venv/bin. This makes shutil.which(ty) / shutil.which(mypy) return None inside the test process even though ty and mypy are dev dependencies present at .venv/bin/ty, .venv/bin/mypy -- unreachable purely because of how the CI step launches the interpreter. This is NOT the T-4352/T-4354/T-4358/T-4359 fixture-project class of bug (a target fixture project lacking ruff/ty as its own dependency) -- this is frob's OWN venv, own dev dependencies. REPRODUCED LOCALLY (linux, mechanism is platform-independent): env -i PATH=/usr/bin:/bin .venv/bin/python -m pytest -q tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config reproduces the exact CI failure: dialects[ty].available is False. Confirmed root cause of these 7 macOS-only failures (CI run 34315257799, head 83a0cecd0): tests/test_gates_suppress.py::TestSuppressionDialects::test_available_reflects_path_not_project_config, tests/test_gates_suppress.py::TestSuppress001Gate::test_mypy_suppressed_ty_unsuppressed_fires, tests/test_gates_suppress.py::TestSuppress001Gate::test_ty_suppressed_mypy_unsuppressed_fires, tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_mypy_suppressed_ty_unsuppressed_gets_paired_suppression, tests/test_gates_fix_engine.py::TestFixSuppress001PairedSuppression::test_idempotent_second_fix_pass_is_a_no_op, tests/test_gates_fix_engine.py::TestSuppress001NoOpSuppressionRefusal::test_no_op_suppression_never_added_under_tests_glob, tests/test_ticket_work_and_land_finish.py::TestAssertTouchedFilesTypeCheckPreLand::test_a_bad_file_outside_fixtures_still_refuses_with_exclude_configured (pre-land type-check stage also resolves its checker via PATH and silently no-ops when absent). FIX: export PATH with .venv/bin prepended before the direct .venv/bin/python -m pytest invocation in the macOS Test step, so the child test process resolves this repo's own dev-dependency tools exactly as uv run would. Do NOT change back to uv run pytest -- that regresses T-4274's pid-capture fix. Keep the direct-interpreter invocation, only fix its PATH. Verify by re-running the reproduction command above with .venv/bin prepended to PATH and confirming it passes. Cannot verify on macOS directly (no macOS access this session); state plainly the CI-green confirmation must come from a macOS run.