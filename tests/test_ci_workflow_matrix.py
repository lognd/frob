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
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        idx = text.find("Diagnose frob check hang on windows")
        assert idx != -1, "windows diag step (T-3589) was removed/renamed"
        # T-3652: slice to the NEXT step (`\n      - name:`) instead of a
        # fixed char budget -- T-3648's added instrumentation (SIGINT/
        # SIGBREAK handler, FROB_WIN32_SPAWN_DEBUG) grew this step past a
        # prior fixed 8000-char window, so the real Start-Process
        # invocation fell outside it and only an unrelated prose comment
        # mentioning "--project" remained inside, silently voiding this
        # assertion (run 33513484322, both POSIX legs). A step-bounded
        # slice tracks the step's real length instead of guessing a size.
        next_step_idx = text.find("\n      - name:", idx + 1)
        step_text = text[idx : next_step_idx if next_step_idx != -1 else idx + 20000]
        assert '"--project", "$env:GITHUB_WORKSPACE",' in step_text, (
            "the diag step's `uv run python <script>` has no --project "
            "pin -- uv resolves the venv from cwd, which has no "
            "pyproject.toml/frob installed unless pinned, so the diag "
            "process dies with ModuleNotFoundError before its "
            "faulthandler watchdog ever arms (T-3597). T-3624 round 12 "
            "moved the invocation to Start-Process -ArgumentList, so "
            "each argument (including --project's value) is now its own "
            "array element rather than one shell-quoted string."
        )

    def test_windows_diag_step_still_scans_the_fixture_not_the_repo(self) -> None:
        """The --project pin must resolve DEPENDENCIES only -- cwd (and so
        frob check's scan target, since the diag script's own sys.argv
        carries no explicit path) must stay at the fixture, not flip to
        scanning this whole repo."""
        # frob:tests .github/workflows/ci.yml
        step = _windows_diag_step()
        assert "-WorkingDirectory $fixture" in step["run"], (
            "expected the diag child's Start-Process invocation to pass "
            "-WorkingDirectory $fixture -- --project must pin DEPENDENCY "
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
    def test_coverage_step_is_gated_to_ubuntu_only(self) -> None:
        """T-3747: the coverage-stamp step must run on ONE OS only.
        Coverage is platform-independent, so running the full suite a
        second time under coverage on every OS duplicated the Test step's
        run (and on windows piled onto the serial-suite long pole). The
        step's block must carry `if: matrix.os == 'ubuntu-latest'`."""
        text = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        idx = text.find("coverage stamp + delta baseline must be freshly")
        assert idx != -1, "the T-1366 coverage-stamp step was removed/renamed"
        next_step_idx = text.find("\n      - name:", idx + 1)
        step_text = text[idx : next_step_idx if next_step_idx != -1 else idx + 4000]
        assert "if: matrix.os == 'ubuntu-latest'" in step_text, (
            "the coverage-stamp step must be gated to ubuntu-latest only -- "
            "coverage is platform-independent and running it on every OS "
            "duplicates the Test step's suite run (T-3747)"
        )

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
    def test_stamp_baseline_is_bare_not_chunked_by_only(self) -> None:
        """T-3740: the coverage-stamp step must run a single bare `frob
        check --stamp-baseline` (no --only). A hand-maintained
        `--stamp-baseline --only <group>` enumeration silently desyncs from
        _stamp_baseline_gate_chunks(): once it stops covering every gate-id
        the chunk accumulator never completes and .frob/baseline is never
        written, yet every command still exits 0. A bare invocation runs
        every chunk in one process and always stamps."""
        text = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        assert "uv run frob check --stamp-baseline\n" in text, (
            "the coverage-stamp step must invoke a single bare `uv run frob "
            "check --stamp-baseline` (T-3740)"
        )
        assert "--stamp-baseline --only" not in text, (
            "no step may chunk --stamp-baseline by --only -- that "
            "enumeration desyncs from _stamp_baseline_gate_chunks() and "
            "silently skips the actual baseline write (T-3740)"
        )

    # frob:tests .github/workflows/ci.yml
    # frob:ticket T-3756
    def test_coverage_step_calls_frob_coverage_full(self) -> None:
        """T-3077 (T-1382 epic): the whole-suite coverage run must go through
        the frob-native `uv run frob coverage --full`, never a `make coverage`
        target (windows-latest ships no `make`). T-3748 had moved that
        invocation into the ubuntu Test step; T-3756 reverted the ubuntu Test
        step to a coverage-free `pytest -q` and restored `frob coverage
        --full` to the dedicated coverage step -- the make-free contract this
        test locks is unchanged either way: the workflow drives coverage
        through frob, not make."""
        text = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        assert "uv run frob coverage --full" in text, (
            "the workflow must run whole-suite coverage via `uv run frob "
            "coverage --full` (T-3077); T-3756 runs it in the coverage step"
        )

    # frob:tests .github/workflows/ci.yml
    # frob:ticket T-3756
    def test_suite_runs_under_coverage_once_not_twice(self) -> None:
        """T-3756 (revert of T-3748): the ubuntu Test step's pass/fail gate
        must be coverage-free (`uv run pytest -q`) -- see the step's own
        comment for why T-3748's combined coverage+test run made ubuntu's
        gate coverage-sensitive and reproducibly red. `uv run frob coverage
        --full` runs separately in the dedicated coverage step (T-1366), as a
        non-blocking best-effort measurement, not the pass/fail gate."""
        text = (
            Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
        ).read_text(encoding="utf-8")
        assert "uv run pytest -q" in text, (
            "the ubuntu Test step must run a coverage-free `uv run "
            "pytest -q` as its pass/fail gate (T-3756)"
        )
        # The coverage-stamp step's own slice must run frob coverage --full
        # as a separate, non-blocking measurement.
        idx = text.find("coverage stamp + delta baseline must be freshly")
        assert idx != -1, "the T-1366 coverage-stamp step was removed/renamed"
        next_step_idx = text.find("\n      - name:", idx + 1)
        step_text = text[idx : next_step_idx if next_step_idx != -1 else idx + 4000]
        assert "uv run frob coverage --full" in step_text, (
            "the coverage-stamp step must run `uv run frob coverage --full` "
            "itself now that the ubuntu Test step is coverage-free (T-3756)"
        )
        assert "--fail-on-degraded" not in step_text, (
            "the coverage step must not gate on --fail-on-degraded -- "
            "coverage is a non-blocking best-effort measurement (T-3756), "
            "backstopped by the step's own continue-on-error: true"
        )


def _windows_diag_step() -> dict:
    """The "Diagnose frob check hang on windows (T-3589)" step's own
    dict from the parsed workflow -- shared by every test below. This is
    variant (a) of the T-3670 round-16 4-variant matrix (current `frob
    check` as-is). Every other variant's name contains "variant" (b/c/d
    below); (a)'s does not, which is what distinguishes it here."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and "variant" not in step.get("name", "")
    )


def _windows_zerospawn_diag_step() -> dict:
    """T-3657 round 15: variant (b) of the 4-variant matrix -- the same
    windows diag as `_windows_diag_step`, but with `FROB_DISABLE_EXEC=1`
    set before `frob.__main__.main()` runs, so none of the 4 guarded
    tool children (git/ruff) this diag exercises are ever spawned. See
    the step's own comment in `.github/workflows/ci.yml` for what
    remains unguarded (frob.gates's ProcessPoolExecutor workers) and
    what a clean vs. still-SIGINT'd run each discriminate. T-3670: run
    33533123354 measured this variant STILL receiving SIGINT, so the
    guarded-child class is now fully exonerated -- see
    `_windows_directpython_diag_step`/`_windows_nopoolpreload_diag_step`
    for the two remaining suspects this ticket's round 16 discriminates."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and "zero-tool-spawn" in step.get("name", "")
    )


def _windows_directpython_diag_step() -> dict:
    """T-3670 round 16: variant (c) of the 4-variant matrix -- the SAME
    diag script and fixture as variant (a), but invoked directly via the
    venv's own python.exe instead of `uv run python ...`, so `uv` never
    appears in the diag child's process ancestry. If this variant is
    clean of `T-3648-SIGNAL` while variant (a) still gets it, `uv` is
    the sender."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and "direct-python" in step.get("name", "")
    )


def _windows_nopoolpreload_diag_step() -> dict:
    """T-3670 round 16: variant (d) of the 4-variant matrix -- the same
    invocation shape as variant (a) (uv ancestry kept, isolating the
    pool alone), but with `FROB_DISABLE_POOL_PRELOAD=1` set before
    `frob.__main__.main()` runs, so `frob.gates`'s `ProcessPoolExecutor`
    preload never constructs. If this variant is clean of
    `T-3648-SIGNAL` while variant (a) still gets it, the pool's
    multiprocessing spawn children are the sender."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and "pool-preload-disabled" in step.get("name", "")
    )


def _windows_trivialpython_diag_step() -> dict:
    """T-3673 round 17: variant (e) -- a control child that NEVER
    imports frob, run through the same Start-Process/uv harness as
    variant (a). Dirty (e) exonerates frob (the environment is the
    sender); clean (e) implicates frob's own startup."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and "trivial-python control" in step.get("name", "")
    )


def _windows_importonly_diag_step() -> dict:
    """T-3673 round 17: variant (f) -- a control child that does
    `import frob` and nothing else. Localizes an import-time side
    effect from anything the check pipeline does afterward."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and "import-only control" in step.get("name", "")
    )


def _windows_mitigation_diag_step() -> dict:
    """T-3673 round 17: variant (a2) -- variant (a) with
    FROB_WIN32_IGNORE_CONSOLE_CTRL=1 set, validating the T-3657
    win32_console_ctrl_ignore_scope() mitigation end to end."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and "mitigation-enabled" in step.get("name", "")
    )


def _windows_stop_before_diag_step(point: str) -> dict:
    """T-3675 round 18 Part 2 / T-3683 round 19: one of the 7
    `FROB_CHECK_STOP_BEFORE=<point>` diag sub-variants -- `point` is one
    of `frob.check._CHECK_STOP_POINTS` ("entry"/"console-scope"/
    "admission" added in round 19, ahead of round 18's original "lock"/
    "detect"/"tasks"/"submit"), each the SAME diag script/fixture as
    variant (a) with only that one env var changed."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return next(
        step
        for step in steps
        if "Diagnose frob check hang on windows" in step.get("name", "")
        and f"stop-before {point} variant" in step.get("name", "")
    )


class TestWindowsZeroSpawnDiagVariant:
    """T-3657 round 15: the SIGINT sender is not one of the 4 guarded
    tool children (T-3651's round-14 hypothesis is falsified -- see this
    module's own docstring and the ticket body for the CREATE_NO_WINDOW
    evidence). This step names whether the sender survives with ZERO
    guarded tool spawns in play."""

    # frob:tests .github/workflows/ci.yml
    def test_zerospawn_diag_step_exists_and_runs_on_windows(self) -> None:
        step = _windows_zerospawn_diag_step()
        assert step.get("if") == "matrix.os == 'windows-latest'"

    # frob:tests .github/workflows/ci.yml
    def test_zerospawn_diag_step_has_a_bounded_timeout(self) -> None:
        step = _windows_zerospawn_diag_step()
        assert step.get("timeout-minutes") == 5, (
            "the zero-tool-spawn diag step must carry its own bounded "
            "timeout-minutes, same as variant (a), so a genuinely wedged "
            "child cannot hang the whole job"
        )

    # frob:tests .github/workflows/ci.yml
    def test_zerospawn_diag_step_sets_frob_disable_exec_before_main(self) -> None:
        run_text = _windows_zerospawn_diag_step()["run"]
        env_idx = run_text.find("FROB_DISABLE_EXEC'] = '1'")
        main_idx = run_text.find("from frob.__main__ import main")
        assert env_idx != -1, (
            "the zero-tool-spawn diag step must set FROB_DISABLE_EXEC=1 "
            "so guarded_subprocess_run refuses every guarded tool spawn "
            "(T-3657 round 15's variant (b))"
        )
        assert main_idx != -1
        assert env_idx < main_idx, (
            "FROB_DISABLE_EXEC=1 must be set BEFORE importing "
            "frob.__main__ -- an import-time spawn (if one ever existed) "
            "must also be covered, not just main()'s own dispatch"
        )

    # frob:tests .github/workflows/ci.yml
    def test_zerospawn_diag_step_reuses_the_same_fixture(self) -> None:
        run_text = _windows_zerospawn_diag_step()["run"]
        assert "-WorkingDirectory $fixture" in run_text, (
            "the zero-tool-spawn variant must scan the SAME diag fixture "
            "as variant (a), not the real repo"
        )

    # frob:tests .github/workflows/ci.yml
    def test_zerospawn_diag_step_pins_project_to_checkout(self) -> None:
        run_text = _windows_zerospawn_diag_step()["run"]
        assert '"--project", "$env:GITHUB_WORKSPACE",' in run_text, (
            "the zero-tool-spawn diag step must pin --project the same "
            "way variant (a) does (T-3597), or uv resolves the venv from "
            "the fixture cwd and the diag process dies with "
            "ModuleNotFoundError before it ever runs"
        )

    # frob:tests .github/workflows/ci.yml
    def test_zerospawn_diag_step_precedes_the_windows_test_step(self) -> None:
        """All four diag variants must run before the real Windows Test
        step, as cheap, sequential pre-flight diagnostics (T-3657's plan
        item 2, extended by T-3670 to 4 variants), not interleaved with
        or after it."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        names = [step.get("name", "") for step in steps]
        original_idx = next(
            i
            for i, name in enumerate(names)
            if "Diagnose frob check hang on windows" in name and "variant" not in name
        )
        zerospawn_idx = next(
            i for i, name in enumerate(names) if "zero-tool-spawn" in name
        )
        directpython_idx = next(
            i for i, name in enumerate(names) if "direct-python" in name
        )
        nopoolpreload_idx = next(
            i for i, name in enumerate(names) if "pool-preload-disabled" in name
        )
        test_idx = next(
            i for i, name in enumerate(names) if name.startswith("Test (windows")
        )
        assert (
            original_idx
            < zerospawn_idx
            < directpython_idx
            < nopoolpreload_idx
            < test_idx
        )


# frob:ticket T-3670
class TestWindowsDirectPythonDiagVariant:
    """T-3670 round 16: variant (c) -- discriminate `uv` as the SIGINT
    sender by invoking the diag script with no `uv` anywhere in its
    process ancestry."""

    # frob:tests .github/workflows/ci.yml
    def test_directpython_diag_step_exists_and_runs_on_windows(self) -> None:
        step = _windows_directpython_diag_step()
        assert step.get("if") == "matrix.os == 'windows-latest'"

    # frob:tests .github/workflows/ci.yml
    def test_directpython_diag_step_has_a_bounded_timeout(self) -> None:
        step = _windows_directpython_diag_step()
        assert step.get("timeout-minutes") == 5, (
            "the direct-python diag step must carry its own bounded "
            "timeout-minutes, same as the other variants, so a genuinely "
            "wedged child cannot hang the whole job"
        )

    # frob:tests .github/workflows/ci.yml
    def test_directpython_diag_step_never_invokes_uv(self) -> None:
        run_text = _windows_directpython_diag_step()["run"]
        assert '-FilePath "uv"' not in run_text, (
            "variant (c)'s whole point is NO uv in the diag child's "
            "process ancestry -- a Start-Process -FilePath 'uv' here "
            "would make this indistinguishable from variant (a)"
        )
        assert "-FilePath $venvPython" in run_text, (
            "variant (c) must invoke the venv's own python.exe directly"
        )

    # frob:tests .github/workflows/ci.yml
    def test_directpython_diag_step_resolves_venv_python_under_workspace(self) -> None:
        run_text = _windows_directpython_diag_step()["run"]
        assert (
            r'$venvPython = Join-Path $env:GITHUB_WORKSPACE ".venv\Scripts\python.exe"'
            in run_text
        ), (
            "variant (c) must resolve the venv python.exe an earlier "
            "'uv sync' step already built under $env:GITHUB_WORKSPACE, "
            "not assume a bare 'python' on PATH"
        )

    # frob:tests .github/workflows/ci.yml
    def test_directpython_diag_step_reuses_the_same_diag_script_and_fixture(
        self,
    ) -> None:
        run_text = _windows_directpython_diag_step()["run"]
        assert "-WorkingDirectory $fixture" in run_text, (
            "variant (c) must scan the SAME diag fixture as variant (a), "
            "not the real repo"
        )
        assert 'Join-Path $env:RUNNER_TEMP "frob_check_diag.py"' in run_text, (
            "variant (c) must reuse variant (a)'s own diag script, not a fork of it"
        )


# frob:ticket T-3670
class TestWindowsNoPoolPreloadDiagVariant:
    """T-3670 round 16: variant (d) -- discriminate `frob.gates`'s
    `ProcessPoolExecutor` preload as the SIGINT sender via
    `FROB_DISABLE_POOL_PRELOAD=1`."""

    # frob:tests .github/workflows/ci.yml
    def test_nopoolpreload_diag_step_exists_and_runs_on_windows(self) -> None:
        step = _windows_nopoolpreload_diag_step()
        assert step.get("if") == "matrix.os == 'windows-latest'"

    # frob:tests .github/workflows/ci.yml
    def test_nopoolpreload_diag_step_has_a_bounded_timeout(self) -> None:
        step = _windows_nopoolpreload_diag_step()
        assert step.get("timeout-minutes") == 5

    # frob:tests .github/workflows/ci.yml
    def test_nopoolpreload_diag_step_sets_env_var_before_main(self) -> None:
        run_text = _windows_nopoolpreload_diag_step()["run"]
        env_idx = run_text.find("FROB_DISABLE_POOL_PRELOAD'] = '1'")
        main_idx = run_text.find("from frob.__main__ import main")
        assert env_idx != -1, (
            "variant (d) must set FROB_DISABLE_POOL_PRELOAD=1 so "
            "frob.gates never constructs its ProcessPoolExecutor"
        )
        assert main_idx != -1
        assert env_idx < main_idx, (
            "FROB_DISABLE_POOL_PRELOAD=1 must be set BEFORE importing "
            "frob.__main__, same posture as variant (b)'s FROB_DISABLE_EXEC"
        )

    # frob:tests .github/workflows/ci.yml
    def test_nopoolpreload_diag_step_keeps_uv_ancestry(self) -> None:
        """Unlike variant (c), variant (d) must NOT change the
        invocation shape -- it isolates the pool alone, so it must still
        go through `uv run`, exactly like variant (a)."""
        run_text = _windows_nopoolpreload_diag_step()["run"]
        assert '"--project", "$env:GITHUB_WORKSPACE",' in run_text

    # frob:tests .github/workflows/ci.yml
    def test_nopoolpreload_diag_step_reuses_the_same_fixture(self) -> None:
        run_text = _windows_nopoolpreload_diag_step()["run"]
        assert "-WorkingDirectory $fixture" in run_text


# frob:ticket T-3673
class TestWindowsTrivialPythonDiagVariant:
    """T-3673 round 17: variant (e) -- discriminate the environment
    itself as the SIGINT sender via a child that never imports frob."""

    # frob:tests .github/workflows/ci.yml
    def test_trivialpython_diag_step_exists_and_runs_on_windows(self) -> None:
        step = _windows_trivialpython_diag_step()
        assert step.get("if") == "matrix.os == 'windows-latest'"

    # frob:tests .github/workflows/ci.yml
    def test_trivialpython_diag_step_has_a_bounded_timeout(self) -> None:
        step = _windows_trivialpython_diag_step()
        assert step.get("timeout-minutes") == 5

    # frob:tests .github/workflows/ci.yml
    def test_trivialpython_diag_step_never_imports_frob(self) -> None:
        run_text = _windows_trivialpython_diag_step()["run"]
        code_lines = [
            line
            for line in run_text.splitlines()
            if '"' in line and not line.strip().startswith('"#')
        ]
        assert not any("import frob" in line for line in code_lines), (
            "variant (e)'s whole point is that the child never imports "
            "frob -- an 'import frob' CODE line here (an explanatory "
            "comment mentioning it is fine) would collapse it into "
            "variant (f)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_trivialpython_diag_step_installs_the_signal_logger(self) -> None:
        run_text = _windows_trivialpython_diag_step()["run"]
        assert "T-3648-SIGNAL" in run_text, (
            "variant (e) must keep the same signal logger preamble as "
            "the other diag variants so a delivered SIGINT is still "
            "observable"
        )
        assert "signal.signal(signal.SIGINT" in run_text

    # frob:tests .github/workflows/ci.yml
    def test_trivialpython_diag_step_just_sleeps(self) -> None:
        run_text = _windows_trivialpython_diag_step()["run"]
        assert "time.sleep(5)" in run_text

    # frob:tests .github/workflows/ci.yml
    def test_trivialpython_diag_step_keeps_uv_ancestry(self) -> None:
        """Same invocation shape as variant (a) -- only the child's own
        code changes, not the process ancestry, so this isolates
        exactly one variable."""
        run_text = _windows_trivialpython_diag_step()["run"]
        assert '"--project", "$env:GITHUB_WORKSPACE",' in run_text


# frob:ticket T-3673
class TestWindowsImportOnlyDiagVariant:
    """T-3673 round 17: variant (f) -- localizes a clean-(e) result to
    either import-time side effects or the check pipeline itself."""

    # frob:tests .github/workflows/ci.yml
    def test_importonly_diag_step_exists_and_runs_on_windows(self) -> None:
        step = _windows_importonly_diag_step()
        assert step.get("if") == "matrix.os == 'windows-latest'"

    # frob:tests .github/workflows/ci.yml
    def test_importonly_diag_step_has_a_bounded_timeout(self) -> None:
        step = _windows_importonly_diag_step()
        assert step.get("timeout-minutes") == 5

    # frob:tests .github/workflows/ci.yml
    def test_importonly_diag_step_imports_frob_and_nothing_else(self) -> None:
        run_text = _windows_importonly_diag_step()["run"]
        assert "import frob" in run_text
        assert "from frob.__main__ import main" not in run_text, (
            "variant (f) must import frob and stop there -- calling "
            "main() would collapse it into variant (a)"
        )
        assert "sys.argv" not in run_text

    # frob:tests .github/workflows/ci.yml
    def test_importonly_diag_step_imports_before_sleeping(self) -> None:
        run_text = _windows_importonly_diag_step()["run"]
        import_idx = run_text.find("import frob")
        sleep_idx = run_text.find("time.sleep(5)")
        assert import_idx != -1 and sleep_idx != -1
        assert import_idx < sleep_idx


# frob:ticket T-3673
class TestWindowsMitigationDiagVariant:
    """T-3673 round 17: variant (a2) -- validates the T-3657
    win32_console_ctrl_ignore_scope() mitigation with
    FROB_WIN32_IGNORE_CONSOLE_CTRL=1."""

    # frob:tests .github/workflows/ci.yml
    def test_mitigation_diag_step_exists_and_runs_on_windows(self) -> None:
        step = _windows_mitigation_diag_step()
        assert step.get("if") == "matrix.os == 'windows-latest'"

    # frob:tests .github/workflows/ci.yml
    def test_mitigation_diag_step_has_a_bounded_timeout(self) -> None:
        step = _windows_mitigation_diag_step()
        assert step.get("timeout-minutes") == 5

    # frob:tests .github/workflows/ci.yml
    def test_mitigation_diag_step_sets_the_env_var(self) -> None:
        step = _windows_mitigation_diag_step()
        assert step.get("env", {}).get("FROB_WIN32_IGNORE_CONSOLE_CTRL") == "1", (
            "variant (a2) must set FROB_WIN32_IGNORE_CONSOLE_CTRL=1 in "
            "the step's own env: block so it is present before uv (and "
            "so frob.__main__) ever starts"
        )

    # frob:tests .github/workflows/ci.yml
    def test_mitigation_diag_step_reuses_variant_a_script_and_fixture(self) -> None:
        run_text = _windows_mitigation_diag_step()["run"]
        assert "-WorkingDirectory $fixture" in run_text
        assert 'Join-Path $env:RUNNER_TEMP "frob_check_diag.py"' in run_text, (
            "variant (a2) must reuse variant (a)'s own diag script"
        )

    # frob:tests .github/workflows/ci.yml
    def test_mitigation_diag_step_fails_the_step_on_exit_130(self) -> None:
        """Acceptance for (a2) is explicit: no exit 130. A silent pass-
        through on 130 would let the mitigation regress unnoticed."""
        run_text = _windows_mitigation_diag_step()["run"]
        assert "-eq 130" in run_text
        assert "did NOT stop the SIGINT" in run_text


# frob:ticket T-3675
class TestWindowsStopBeforeDiagVariants:
    """T-3675 round 18 Part 2 / T-3683 round 19: the 7 FROB_CHECK_STOP_
    BEFORE sub-variants bisecting run_check's own pre-lock-through-
    submit pipeline."""

    _POINTS = (
        "entry",
        "console-scope",
        "admission",
        "lock",
        "detect",
        "tasks",
        "submit",
    )

    # frob:tests tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants.test_all_seven_points_have_their_own_step  # noqa: E501
    def test_all_seven_points_have_their_own_step(self) -> None:
        for point in self._POINTS:
            step = _windows_stop_before_diag_step(point)
            assert step.get("if") == "matrix.os == 'windows-latest'"

    # frob:tests tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants.test_all_seven_have_a_bounded_timeout  # noqa: E501
    def test_all_seven_have_a_bounded_timeout(self) -> None:
        for point in self._POINTS:
            step = _windows_stop_before_diag_step(point)
            assert step.get("timeout-minutes") == 5

    # frob:tests tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants.test_each_step_sets_its_own_matching_point  # noqa: E501
    def test_each_step_sets_its_own_matching_point(self) -> None:
        for point in self._POINTS:
            step = _windows_stop_before_diag_step(point)
            assert step.get("env", {}).get("FROB_CHECK_STOP_BEFORE") == point

    # frob:tests tests/test_ci_workflow_matrix.py::TestWindowsStopBeforeDiagVariants.test_each_step_reuses_variant_a_script_and_fixture  # noqa: E501
    def test_each_step_reuses_variant_a_script_and_fixture(self) -> None:
        for point in self._POINTS:
            run_text = _windows_stop_before_diag_step(point)["run"]
            assert "-WorkingDirectory $fixture" in run_text
            assert 'Join-Path $env:RUNNER_TEMP "frob_check_diag.py"' in run_text


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
    """T-3609 (T-3604 round 8 correction): a step-level continue-on-
    error is redundant AND wrong -- T-3604's own script-side elapsed-
    time discriminator already exits 0 for every no-hang outcome (a
    clean run or an ordinary gate finding like CHECK001), so the only
    nonzero left IS a genuine watchdog-fired hang, which SHOULD fail
    the (job-level-advisory) windows job loudly. A step-level continue-
    on-error also tripped tests/unit/test_release_workflow_gate.py::
    TestCiWindowsLegAdvisoryOnly::
    test_no_step_level_continue_on_error_smuggled_onto_other_legs on
    BOTH posix legs (run 33451274911) -- that guard is correct and
    stays; this diag step must not carry step-level continue-on-error
    at all."""

    # frob:tests .github/workflows/ci.yml
    def test_step_has_no_continue_on_error(self) -> None:
        step = _windows_diag_step()
        assert "continue-on-error" not in step, (
            "the windows diag step must NOT set its own continue-on-"
            "error -- T-3604's script-side elapsed-time discriminator "
            "already exits 0 for every no-hang outcome, so a step-level "
            "continue-on-error is both redundant and trips the repo's "
            "windows-only advisory-boundary guard test (T-3609)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_uses_start_process_not_a_native_pwsh_command(
        self,
    ) -> None:
        """T-3609's original concern (a native pwsh command's stderr
        redirect turning under Stop into a terminating NativeCommand
        Error) applies to whatever pwsh invokes NATIVELY as a bare
        command. T-3624 round 10's `cmd /c` wrapper was ITSELF invoked as
        a native pwsh command and died silently at that exact boundary
        (round 11, run 33480116817) -- round 12 replaces both the `uv`
        invocation and the `cmd /c` wrapper around it with `Start-
        Process`, which pwsh never treats as a native command at all, so
        neither stream-redirect promotion nor a silent kill at the
        invocation line can recur."""
        step = _windows_diag_step()
        assert "Start-Process" in step["run"]
        code_lines = [
            line
            for line in step["run"].splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert not any("cmd /c" in line for line in code_lines), (
            "the cmd /c wrapper (T-3624 round 10) died silently at its "
            "own invocation line (round 11, run 33480116817) -- round 12 "
            "removes it entirely in favor of Start-Process (a historical "
            "mention of 'cmd /c' in an explanatory comment is fine, only "
            "actual CODE using it is not)"
        )

    def test_diag_invocation_redirects_uv_streams_to_files(self) -> None:
        """The uv/python invocation, run through Start-Process rather
        than a native pwsh/cmd command, still captures both streams to
        files so breadcrumb output survives even a killed/terminated
        child (T-3624 round 12)."""
        step = _windows_diag_step()
        assert "-RedirectStandardOutput $diagOut" in step["run"]
        assert "-RedirectStandardError $diagErr" in step["run"]

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_is_wrapped_in_try_catch(self) -> None:
        """T-3624 round 12: the whole Start-Process/Wait-Process region is
        wrapped in try/catch printing 'invoke threw: $_' -- round 11's
        failure mode was a silent kill with zero diagnostic output, so no
        exception path through this invocation may ever go unreported
        again."""
        run_text = _windows_diag_step()["run"]
        assert "invoke threw: $_" in run_text, (
            "expected the diag step's Start-Process invocation to be "
            "wrapped in a try/catch that prints 'invoke threw: $_' on "
            "any exception -- otherwise a failure mode this step has not "
            "yet seen could die as silently as round 11's cmd /c did"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_invocation_output_capture_is_unconditional(self) -> None:
        """T-3624 round 12: Get-Content of both redirect files and the
        exit-code print must run in a `finally` block, not only on the
        happy path -- round 11 died with NO output at all because
        everything after the invocation line was unreachable once it
        threw."""
        run_text = _windows_diag_step()["run"]
        finally_idx = run_text.find("} finally {")
        assert finally_idx != -1, (
            "expected a `finally` block around the diag invocation's "
            "output-capture/exit-code reporting"
        )
        finally_block = run_text[finally_idx:]
        assert "Get-Content $diagOut" in finally_block
        assert "Get-Content $diagErr" in finally_block
        assert "frob check diag exit code:" in finally_block

    # frob:tests .github/workflows/ci.yml
    def test_diag_step_sets_error_action_preference_continue_first(self) -> None:
        """T-3619 (round 9): pwsh steps default to
        $ErrorActionPreference='Stop', which promotes a native command's
        FIRST stderr line into a terminating error -- this is the actual
        mechanism that killed rounds 7 (uv resolver chatter) and 8/9
        (frob's own gitio WARNING), independent of the T-3609 stderr-
        redirect fix, since Stop kills the step on interleaved stderr
        too. The step script must flip to Continue before any command
        that can write to stderr runs."""
        step = _windows_diag_step()
        code_lines = [
            line
            for line in step["run"].splitlines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert code_lines, "diag step has no run lines"
        assert (
            code_lines[0].strip().startswith("$ErrorActionPreference = 'Continue'")
        ), (
            "the diag step's first non-blank run line must set "
            "$ErrorActionPreference = 'Continue' -- otherwise the "
            "default Stop preference turns the first stderr line any "
            "native command prints (uv chatter, frob's gitio warnings) "
            "into a terminating NativeCommandError before the script's "
            "own elapsed-time/exit-code handling ever runs (T-3619)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_fixture_repo_has_an_initial_commit(self) -> None:
        """T-3619 (round 9): the fixture repo is `git init` with zero
        commits, so frob's gitio helper (`git rev-parse --abbrev-ref
        HEAD`) fails rc=128 with "ambiguous argument 'HEAD'" and frob
        aborts with "frob: interrupted" before the diagnostic's own
        watchdog/exit-code logic ever gets a signal to read. The step
        must create one empty commit right after `git init`."""
        step = _windows_diag_step()
        run_lines = step["run"].splitlines()
        init_idx = next(i for i, line in enumerate(run_lines) if "git init" in line)
        following = "\n".join(run_lines[init_idx + 1 : init_idx + 4])
        assert "commit" in following and "--allow-empty" in following, (
            "expected a `git commit --allow-empty` shortly after `git "
            "init` in the diag step -- a commitless fixture repo makes "
            "frob's own git rev-parse HEAD fail rc=128 and frob abort "
            "with 'frob: interrupted' (T-3619)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_python_prints_liveness_marker_before_anything_else(self) -> None:
        """T-3624 round 10: the diag python script's FIRST statement
        prints a liveness marker (flushed) before even `import
        faulthandler` -- if diag.out ever comes back empty, that proves
        the interpreter itself never ran a single statement, ruling out
        the whole python process as the kill point."""
        step = _windows_diag_step()
        code_line_idx = next(
            i
            for i, line in enumerate(step["run"].splitlines())
            if "$codeLines = @(" in line
        )
        first_code_line = step["run"].splitlines()[code_line_idx + 1]
        assert "diag-python-alive" in first_code_line, (
            "the diag script's first $codeLines entry must print a "
            "liveness marker -- otherwise an empty diag.out cannot "
            "distinguish 'python never started' from 'python started and "
            "then died silently'"
        )

    # frob:tests .github/workflows/ci.yml
    def test_diag_python_wraps_main_call_in_baseexception_handler(self) -> None:
        """T-3624 round 10: main() is called inside try/except
        BaseException that prints the exception's repr and a full
        traceback before re-raising -- so whatever "frob: interrupted"
        actually is gets a stack instead of dying with no diagnostic
        information at all."""
        run_text = _windows_diag_step()["run"]
        assert "except BaseException as exc:" in run_text
        assert "traceback.print_exc()" in run_text

    # frob:tests .github/workflows/ci.yml
    def test_diag_step_has_breadcrumbs_around_every_major_block(self) -> None:
        """T-3624 round 10: Write-Host markers before/after fixture
        setup, diag-file writing, and the child invocation -- whichever
        marker is the LAST to print in a real run localizes the kill
        point, since the step previously died with zero output of its
        own at all."""
        run_text = _windows_diag_step()["run"]
        for marker in (
            "fixture dir + pyproject.toml written",
            "fixture git init + initial commit done",
            "diag python file written",
            "about to invoke uv via Start-Process",
            "Start-Process invocation returned",
        ):
            assert marker in run_text, f"expected a breadcrumb containing {marker!r}"

    # frob:tests .github/workflows/ci.yml
    def test_test_step_sets_frob_test_ignore_console_ctrl(self) -> None:
        """T-3673 round 17: the windows Test step is the ONE place in
        this repo that sets FROB_TEST_IGNORE_CONSOLE_CTRL=1, activating
        tests/conftest.py's session-lifetime console-ctrl-ignore guard
        -- see docs/modules/process.md's "Round 17" paragraph."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        assert test_step.get("env", {}).get("FROB_TEST_IGNORE_CONSOLE_CTRL") == "1"

    # frob:tests .github/workflows/ci.yml
    def test_test_step_sets_frob_test_hard_exit(self) -> None:
        """T-3675 round 18 Part 1: the windows Test step is the ONE
        place in this repo that sets FROB_TEST_HARD_EXIT=1, activating
        tests/conftest.py's session-teardown hard-exit escape hatch --
        see docs/modules/process.md's "Round 18" paragraph."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        assert test_step.get("env", {}).get("FROB_TEST_HARD_EXIT") == "1"

    # frob:tests .github/workflows/ci.yml
    def test_test_step_sets_frob_test_midrun_watchdog_seconds(self) -> None:
        """T-3683 round 19 Part B: the windows Test step is the ONE
        place in this repo that sets FROB_TEST_MIDRUN_WATCHDOG_SECONDS,
        arming tests/conftest.py's mid-run watchdog -- see docs/modules/
        process.md's "Round 19" paragraph."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        raw = test_step.get("env", {}).get("FROB_TEST_MIDRUN_WATCHDOG_SECONDS")
        assert raw is not None
        assert float(raw) > 0
        assert float(raw) < 1500, (
            "the watchdog threshold must be comfortably INSIDE this "
            "step's own 1500s budget, or it can never fire before the "
            "external Wait-Process timeout does"
        )

    # frob:tests .github/workflows/ci.yml
    # frob:waive DUP001 reason="matches this class's established \
    # one-assertion-per-flag shape (see \
    # test_test_step_sets_frob_test_ignore_console_ctrl/_hard_exit/ \
    # _midrun_watchdog_seconds above); extracting a shared helper would obscure which \
    # single Test-step property each self-contained, frob:tests-anchored test covers"
    def test_win32_test_step_raises_per_test_timeout_to_600(self) -> None:
        """T-3757: the windows Test step must pass --timeout=600 on the
        pytest command line (overriding pyproject's --timeout=120
        addopts) so a per-test hang gets 600s, not 120s, before
        pytest-timeout fires -- utility check that the override stays
        present in the Start-Process ArgumentList."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        run_text = test_step.get("run", "")
        assert '"--timeout=600"' in run_text, (
            "windows Test step's pytest invocation must carry "
            '"--timeout=600" in its ArgumentList'
        )

    # frob:tests .github/workflows/ci.yml
    def test_win32_test_step_surfaces_failure_tracebacks(self) -> None:
        """T-3785: the windows Test step must pass -rA and --tb=short on
        the pytest command line so a full-suite failure's traceback
        (not just its SUITE-RESULT-FAILED node id) reaches the job log --
        needed to diagnose the doctor-cluster tests that only fail under
        the full Windows suite, never under isolated winrun."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        run_text = test_step.get("run", "")
        assert '"-rA"' in run_text, (
            "windows Test step's pytest invocation must carry "
            '"-rA" in its ArgumentList'
        )
        assert '"--tb=short"' in run_text, (
            "windows Test step's pytest invocation must carry "
            '"--tb=short" in its ArgumentList'
        )

    def test_test_step_is_untouched_and_still_windows_only(self) -> None:
        """Neither T-3604 nor T-3609 may touch the Test step itself --
        only the diagnostic step ahead of it."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        assert test_step["if"] == "matrix.os == 'windows-latest'"
        assert "continue-on-error" not in test_step, (
            "T-3604 must not add continue-on-error to the Test step "
            "itself -- only to the diagnostic step ahead of it"
        )


class TestTestStepsNoRerunFlakes:
    """T-3776 reverted (T-3777): pytest-rerunfailures 16.6 INTERNALERRORs
    under xdist on py3.14 (macos), turning a rare flake into a
    deterministic whole-suite abort. --reruns/--reruns-delay must not be
    present on any of the three platforms' Test steps; flakes are handled
    by fixing the specific flaky tests instead (T-3775)."""

    # frob:tests \
    # tests/test_ci_workflow_matrix.py::TestTestStepsNoRerunFlakes.test_ubuntu_test_ste\
    # p_no_reruns_flakes
    def test_ubuntu_test_step_no_reruns_flakes(self) -> None:
        """The ubuntu Test step's pytest invocation must not carry
        --reruns/--reruns-delay (T-3777)."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (ubuntu")
        )
        run_text = test_step.get("run", "")
        assert "uv run pytest -q" in run_text
        assert "--reruns" not in run_text, (
            "ubuntu Test step's pytest invocation must not carry --reruns (T-3777)"
        )

    def test_macos_test_step_no_reruns_flakes(self) -> None:
        """The macos Test step's pytest invocation must not carry
        --reruns/--reruns-delay (T-3777)."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (macos")
        )
        run_text = test_step.get("run", "")
        assert "uv run pytest -q" in run_text
        assert "--reruns" not in run_text, (
            "macos Test step's pytest invocation must not carry --reruns (T-3777)"
        )

    def test_windows_test_step_no_reruns_flakes(self) -> None:
        """The windows Test step's Start-Process ArgumentList must not
        carry --reruns/--reruns-delay (T-3777)."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        run_text = test_step.get("run", "")
        assert '"--reruns"' not in run_text, (
            "windows Test step's pytest invocation must not carry --reruns (T-3777)"
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


def _code_lines_array_lines() -> list[str]:
    """The raw lines of the diag step's `$codeLines = @( ... )` pwsh
    array literal, from the line after `@(` up to (excluding) the
    closing `)` line -- shared by the syntactic-balance tests below."""
    run_lines = _windows_diag_step()["run"].splitlines()
    start = next(i for i, line in enumerate(run_lines) if "$codeLines = @(" in line)
    end = next(
        i for i in range(start + 1, len(run_lines)) if run_lines[i].strip() == ")"
    )
    return run_lines[start + 1 : end]


def _strip_inline_comment(line: str) -> str:
    """Strip a trailing pwsh `# ...` comment from an element line, if the
    `#` appears AFTER the last quote character (i.e. genuinely outside
    the string literal) -- a naive `line.split('#')[0]` would wrongly
    truncate a quoted string that happens to contain a literal `#`."""
    last_quote = max(line.rfind("'"), line.rfind('"'))
    hash_idx = line.find("#", last_quote + 1) if last_quote != -1 else line.find("#")
    return line if hash_idx == -1 else line[:hash_idx]


class TestCodeLinesArrayLiteralIsSyntacticallyBalanced:
    """T-3633 (round 11): pwsh is not available on this (WSL) CI host, so
    a ParserError in the $codeLines array literal can only ever be
    caught by a human reading a failed job log after the fact. This
    statically re-derives pwsh's own array-literal balance rule so a
    future round's edit gets caught before it ever reaches a runner:
    round 10 shipped exactly this defect -- a trailing comma after the
    last element ("    raise",) right before the closing `)` -- and
    NONE of that round's instrumentation ever ran (run 33472403980,
    ParserError at ~0.5s, before even the liveness-marker print)."""

    # frob:tests .github/workflows/ci.yml
    def test_last_array_element_has_no_trailing_comma(self) -> None:
        """pwsh's `@()` array grammar treats a bare trailing `,` as an
        operator expecting a following expression -- a comma right
        before the closing `)` is a hard ParserError ("Missing
        expression after ','"), unlike Python/JS where it is tolerated.
        The LAST non-blank, non-comment line inside the array must NOT
        end with a comma once any trailing inline `# ...` comment is
        stripped."""
        content_lines = [
            line
            for line in _code_lines_array_lines()
            if line.strip() and not line.strip().startswith("#")
        ]
        assert content_lines, "expected at least one element in $codeLines"
        last = _strip_inline_comment(content_lines[-1]).rstrip()
        assert not last.endswith(","), (
            f"the last $codeLines element {last!r} ends with a trailing "
            "comma -- pwsh's array grammar parses that as 'expecting "
            "another expression', a hard ParserError right before the "
            "closing ')' (T-3633, exactly what run 33472403980 hit)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_every_non_last_element_line_ends_with_a_comma(self) -> None:
        """Every element EXCEPT the last must end with a comma (ignoring
        any trailing inline `# ...` comment) -- a missing comma between
        two adjacent element strings would make pwsh parse them as one
        juxtaposed expression instead of two separate array entries,
        silently corrupting the emitted python source instead of raising
        a ParserError."""
        content_lines = [
            line
            for line in _code_lines_array_lines()
            if line.strip() and not line.strip().startswith("#")
        ]
        for line in content_lines[:-1]:
            stripped = _strip_inline_comment(line).rstrip()
            assert stripped.endswith(","), (
                f"$codeLines element {stripped!r} does not end with a "
                "comma but is not the last element -- pwsh would parse "
                "it and the next element as one juxtaposed expression "
                "instead of two separate array entries"
            )
