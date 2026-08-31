"""T-2917: CI ran ubuntu-latest only, so no platform regression (Windows or
macOS) could ever be detected -- locks that the `build` job's matrix
includes windows-latest and macos-latest alongside ubuntu-latest.
"""

from pathlib import Path

import yaml


def _load_ci_workflow() -> dict:
    """Parse .github/workflows/ci.yml (frob:tests target) into a dict."""
    text = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    return yaml.safe_load(text)


class TestCiBuildMatrixCoversAllThreePlatforms:
    """T-2917: a single-OS CI matrix cannot detect a platform regression."""

    def test_build_job_declares_a_matrix_strategy(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        build_job = workflow["jobs"]["build"]
        assert "strategy" in build_job, (
            "build job has no matrix strategy -- it can only ever run on "
            "one OS, so a Windows- or macOS-only regression is undetectable"
        )
        assert build_job["runs-on"] == "${{ matrix.os }}"

    def test_build_matrix_includes_windows_and_macos(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        matrix_os = workflow["jobs"]["build"]["strategy"]["matrix"]["os"]
        assert "ubuntu-latest" in matrix_os
        assert "windows-latest" in matrix_os
        assert "macos-latest" in matrix_os

    def test_build_matrix_is_fail_fast_false(self) -> None:
        """A single early platform failure must not hide the others' results."""
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        strategy = workflow["jobs"]["build"]["strategy"]
        assert strategy.get("fail-fast") is False


class TestWindowsDiagStepResolvesFrobCheckoutEnv:
    """T-3597: the "Diagnose frob check hang on windows (T-3589)" step
    `Push-Location`s into a throwaway fixture directory before invoking
    `uv run python <diag script>` -- with no `--project`, `uv` resolves
    the venv/dependencies from the CURRENT DIRECTORY, which is the
    fixture (no pyproject.toml, no `frob` installed), not the frob
    checkout. The diag process dies with `ModuleNotFoundError: No module
    named 'frob'` before the faulthandler watchdog it exists to arm ever
    runs, silently voiding the whole Windows-hang diagnostic (run
    33412543005). `--project $env:GITHUB_WORKSPACE` pins dependency
    resolution to the checkout while leaving cwd (and so `frob check`'s
    scan target) at the fixture."""

    def test_windows_diag_step_uv_run_pins_project_to_checkout(self) -> None:
        # frob:tests .github/workflows/ci.yml
        text = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "ci.yml"
        ).read_text(encoding="utf-8")
        idx = text.find("Diagnose frob check hang on windows")
        assert idx != -1, "windows diag step (T-3589) was removed/renamed"
        step_text = text[idx : idx + 4000]
        assert "uv run --project $env:GITHUB_WORKSPACE python" in step_text, (
            "the diag step's `uv run python <script>` has no --project "
            "pin -- uv resolves the venv from cwd (Push-Location'd into "
            "the throwaway fixture, which has no pyproject.toml/frob "
            "installed), so the diag process dies with ModuleNotFoundError "
            "before its faulthandler watchdog ever arms (T-3597)"
        )

    def test_windows_diag_step_still_scans_the_fixture_not_the_repo(self) -> None:
        """The --project pin must resolve DEPENDENCIES only -- cwd (and so
        frob check's scan target, since the diag script's own sys.argv
        carries no explicit path) must stay at the fixture, not flip to
        scanning this whole repo."""
        # frob:tests .github/workflows/ci.yml
        text = (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "ci.yml"
        ).read_text(encoding="utf-8")
        idx = text.find("Diagnose frob check hang on windows")
        assert idx != -1
        step_text = text[idx : idx + 4000]
        run_idx = step_text.find("uv run --project")
        assert run_idx != -1
        preceding = step_text[:run_idx]
        assert preceding.rstrip().splitlines()[-1].strip() == "Push-Location $fixture", (
            "the uv invocation must still be immediately preceded by "
            "Push-Location $fixture -- --project must pin DEPENDENCY "
            "resolution only, not also move frob check's scan target off "
            "the fixture and onto the real repo"
        )


class TestCoverageStepUsesFrobNotMake:
    """T-3077 (T-1382 epic: decouple frob from the Makefile): the T-1366
    "coverage stamp + delta baseline" step used to shell out to `make
    coverage`, which depends on a `make` binary that windows-latest never
    installs -- so the one job that would prove the make-free path works
    never actually exercised it. The step must call `uv run frob coverage
    --full` directly instead."""

    # frob:tests .github/workflows/ci.yml
    def test_coverage_step_does_not_shell_to_make(self) -> None:
        """No CI step may spell `make coverage`/`make <target>` -- T-1382's
        whole point is that workflows never depend on a Makefile."""
        workflow = _load_ci_workflow()
        raw = yaml.safe_dump(workflow)
        assert "make coverage" not in raw, (
            "a CI step still shells to `make coverage`, which depends on a "
            "`make` binary no step installs on windows-latest (T-3077)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_coverage_step_calls_frob_coverage_full(self) -> None:
        """The T-1366 coverage-stamp step's `run:` block must invoke the
        frob subcommand `make coverage` used to alias, not the make target
        itself."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        coverage_step = next(
            step
            for step in steps
            if "coverage stamp" in step.get("name", "")
        )
        assert "uv run frob coverage --full" in coverage_step["run"], (
            "the T-1366 coverage-stamp step must call `uv run frob "
            "coverage --full` directly (T-3077)"
        )


def _windows_diag_step() -> dict:
    """The "Diagnose frob check hang on windows (T-3589)" step's own
    dict from the parsed workflow -- shared by every test below."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
    )


class TestWindowsDiagStepFixtureIsAClassifiableProject:
    """T-3604 (T-3589 round 7): run 33439890956 measured `frob check`
    COMPLETING in 547ms on the diag fixture and still aborting the
    windows job, because a bare src/demo/__init__.py with no
    pyproject.toml makes project-type detection legitimately yield
    'unknown' (CHECK001) -- a real gate ERROR, not a hang. The fixture
    must be a classifiable Python project."""

    # frob:tests .github/workflows/ci.yml
    def test_fixture_gets_a_pyproject_toml(self) -> None:
        step = _windows_diag_step()
        assert "pyproject.toml" in step["run"], (
            "the diag fixture has no pyproject.toml -- frob's project-"
            "type detection yields 'unknown' (CHECK001) and the step "
            "fast-fails before ever exercising a real language stage "
            "(T-3604, run 33439890956)"
        )


class TestWindowsDiagStepDoesNotGateTheJob:
    """T-3604: this diagnostic step must never abort the job before the
    Test step runs -- a `frob check` gate finding on the fixture (e.g.
    the CHECK001 this ticket fixes) is not a hang and must not block the
    step that actually produces the data this CI run exists to collect."""

    # frob:tests .github/workflows/ci.yml
    def test_step_has_continue_on_error(self) -> None:
        step = _windows_diag_step()
        assert step.get("continue-on-error") is True, (
            "the windows diag step must set continue-on-error: true so "
            "a gate finding on the fixture (or any other non-hang "
            "nonzero exit) cannot abort the job before the Test step "
            "runs (T-3604)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_test_step_is_untouched_and_still_windows_only(self) -> None:
        """T-3604 must not touch the Test step itself -- only add
        continue-on-error to the diagnostic step ahead of it."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step
            for step in steps
            if step.get("name", "").startswith("Test (windows")
        )
        assert test_step["if"] == "matrix.os == 'windows-latest'"
        assert "continue-on-error" not in test_step, (
            "T-3604 must not add continue-on-error to the Test step "
            "itself -- only to the diagnostic step ahead of it"
        )


class TestWindowsDiagStepRunsUnbudgeted:
    """T-3604: a `--budget 180` diag run defers gates-security/lint/
    static to a later, unmeasured pass -- a real hang living in one of
    those deferred stage groups would never reach the fixture at all.
    The diag invocation must run unbudgeted so all 5 stage groups are
    exercised against the fixture."""

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_has_no_budget_flag(self) -> None:
        step = _windows_diag_step()
        assert "--budget" not in step["run"], (
            "the diag invocation still passes --budget, which defers "
            "gates-security/lint/static -- a hang in one of those stage "
            "groups would never reach this diagnostic (T-3604)"
        )
