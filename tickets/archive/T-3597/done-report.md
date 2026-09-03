## Done report

Changed:
.github/workflows/ci.yml (Diagnose frob check hang on windows T-3589 step)
tests/test_ci_workflow_matrix.py::TestWindowsDiagStepResolvesFrobCheckoutEnv

Evidence:
tests/test_ci_workflow_matrix.py::TestWindowsDiagStepResolvesFrobCheckoutEnv::test_windows_diag_step_uv_run_pins_project_to_checkout
tests/test_ci_workflow_matrix.py::TestWindowsDiagStepResolvesFrobCheckoutEnv::test_windows_diag_step_still_scans_the_fixture_not_the_repo

Pinned `uv run --project $env:GITHUB_WORKSPACE python <diag script>` so
uv resolves the frob checkout's own venv/deps instead of the fixture
directory's (nonexistent) project -- cwd stays Push-Location'd at the
fixture so frob check's scan target is unchanged. Manually verified the
designated repro test fails against the pre-fix ci.yml (checked out at
the parent commit, ran locally, then restored) and passes against the
fix; forced the BUG002 designation since the tool's --check-repro
cannot verify a not-yet-committed pre-land diff (T-2025 documented
limitation), same pattern used for T-3571's evidence this session.

Filed: none

Gates: frob check --ticket T-3597 clean on gate:SCOPE/gate:PRE/gate:AFFECT;
repo-wide failures from an unscoped run are pre-existing (T-3590).
