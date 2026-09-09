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


class TestWindowsTestStepMitigationsStayPinned:
    """T-3673/T-3675/T-3683/T-3757/T-3785: the windows Test step itself
    (not the now-deleted diagnostic scaffolding that preceded it, see
    T-4265) carries several permanent mitigations that came out of the
    hang investigation -- these lock them in place independent of the
    diagnostic steps' own lifecycle."""

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

    # frob:tests .github/workflows/ci.yml
    def test_win32_test_step_caps_workers_at_n2(self) -> None:
        """T-4360: the windows Test step must pass "-n","2" on the pytest
        command line (overriding pyproject's `-n auto` addopts, same
        last-`-n`-wins precedent as the --timeout override above) --
        measured, not guessed: two frob_self_scan_heavy-group workers
        each died independently ~300s in with no timeout dump (suspect
        OOM) under -n auto's 4-worker fanout on a real run
        (34315257799); halving worker count halves the dominant ambient
        term in that memory arithmetic. See tickets/T-4360/
        measurement-notes.md for the full measurement."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        run_text = test_step.get("run", "")
        assert '"-n","2"' in run_text, (
            'windows Test step\'s pytest invocation must carry "-n","2" '
            "in its ArgumentList to cap worker count below -n auto's "
            "4-worker fanout"
        )

    def test_test_step_is_untouched_and_still_windows_only(self) -> None:
        """The windows Test step must stay gated to windows-latest and
        must never carry its own continue-on-error (that stays on the
        job's advisory `continue-on-error` flag, T-4236, not this step;
        see T-3604/T-3609, whose diagnostic step this test used to
        distinguish the real Test step from was removed in T-4265)."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (windows")
        )
        assert test_step["if"] == "matrix.os == 'windows-latest'"
        assert "continue-on-error" not in test_step, (
            "the windows Test step itself must not carry its own continue-on-error"
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
        --reruns/--reruns-delay (T-3777).

        T-4274: the invocation itself changed from `uv run pytest -q` to
        `.venv/bin/python -m pytest -q` (backgrounding `uv run` put the
        wrong pid behind `$!`, so the step's own SIGABRT-for-a-stack-dump
        aborted `uv` instead of the interpreter -- see
        TestMacosTestStepSignalsTheRealInterpreter in
        test_ci_workflow_timeout.py for the full T-4274 lock) -- this
        test's own concern (no --reruns flag) is invocation-shape
        agnostic, so it checks for `pytest -q` rather than the specific
        `uv run` prefix."""
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        test_step = next(
            step for step in steps if step.get("name", "").startswith("Test (macos")
        )
        run_text = test_step.get("run", "")
        assert "pytest -q" in run_text
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


class TestSelfGateRunsOnWindowsEvenIfTestStepFails:
    """T-4269: GitHub Actions' default per-step `if: success()` skips
    every step after the first failure in a job, so a failing windows
    Test step silently skipped the self-gate step after it -- gates have
    therefore NEVER actually run on windows, independent of whether the
    Test step's own failures were real. Locks that the self-gate step's
    run condition was widened to also fire on windows regardless of
    upstream step outcome, while leaving ubuntu/macos on their existing
    fail-fast `success()` behavior."""

    # frob:tests .github/workflows/ci.yml
    def test_self_gate_step_runs_on_windows_after_a_prior_failure(self) -> None:
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        gate_step = next(
            step for step in steps if step.get("name") == "frob check (self-gate)"
        )
        condition = gate_step.get("if", "")
        assert "matrix.os == 'windows-latest'" in condition, (
            "self-gate step's `if:` must special-case windows-latest so a "
            "failing Test step does not silently skip it"
        )
        assert "success()" in condition, (
            "ubuntu/macos must keep their existing success()-gated "
            "fail-fast behavior -- the windows special-case must be "
            "ADDED, not a wholesale replacement of success()"
        )
        assert "cancelled()" in condition, (
            "the widened condition must still exclude a genuinely "
            "cancelled run (bare `success() || matrix.os == "
            "'windows-latest'` would not)"
        )
