"""T-3192: a hanging ubuntu-latest job produced NO failure signal -- the
owner had to cancel run 33135896391 by hand after 54 minutes (runs
33032904841 and 32968539246 sit in history as `cancelled`, never
`failure`, for the same reason). These lock the two structural guards
this ticket adds: a job-level `timeout-minutes` backstop, and a
`timeout -s ABRT`-wrapped ubuntu Test step (paired with
`PYTHONFAULTHANDLER=1`) that turns a hang into a FAILURE with a stack
dump naming where it was stuck, not just a bare timeout message.

The actual stack-dump mechanism is proven separately by a real planted
hang under `tests/system/test_ci_hang_guard_positive_control.py` (T-3192)
-- this file only locks the workflow YAML's structure, mirroring
tests/test_ci_workflow_matrix.py's own T-2917 precedent for the same
file.
"""

from pathlib import Path

import yaml


def _load_ci_workflow() -> dict:
    """Parse .github/workflows/ci.yml (frob:tests target) into a dict."""
    text = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    return yaml.safe_load(text)


# frob:ticket T-4274
def _all_pytest_steps() -> list[dict]:
    """Every `build` job step whose `run` invokes pytest at all -- the
    one "walk every step, keep the pytest-invoking ones" scan shared by
    `_pytest_test_step` (below) and
    `TestUbuntuTestStepIsTimedWithStackDump.test_a_non_gated_pytest_step_
    still_exists_for_other_platforms` (DUP001 extraction, T-4274): both
    used to independently re-derive this identical list comprehension."""
    workflow = _load_ci_workflow()
    steps = workflow["jobs"]["build"]["steps"]
    return [s for s in steps if isinstance(s.get("run"), str) and "pytest" in s["run"]]


# frob:ticket T-4274
# frob:waive WIRE001 reason="genuinely wired -- called by \
# test_macos_step_backgrounds_the_interpreter_directly_not_uv_run below and by \
# TestUbuntuTestStepIsTimedWithStackDump._ubuntu_test_step/TestMacosTestStepSignalsTheR\
# ealInterpreter._macos_test_step, both themselves called by every test method in \
# their class; a pure workflow-YAML-inspection test helper has no production caller to \
# reach it through by construction, the same shape this file's own pre-existing \
# _load_ci_workflow/_ubuntu_test_step helpers are in" follow_up="T-4274"
def _pytest_test_step(name_prefix: str) -> dict:
    """The single pytest-invoking `build` job step whose `name` starts
    with `name_prefix` -- shared by `TestUbuntuTestStepIsTimedWithStack
    Dump`/`TestMacosTestStepSignalsTheRealInterpreter` (DUP001 extraction,
    T-4274): both classes located "their" platform's Test step the same
    way modulo the matched prefix, so this is that one lookup with the
    prefix as its only parameter."""
    candidates = [s for s in _all_pytest_steps() if s.get("name", "").startswith(name_prefix)]
    assert candidates, f"no step named {name_prefix!r} invokes pytest at all"
    return candidates[0]


# frob:ticket T-3192
class TestBuildJobHasATimeoutBackstop:
    """A hang landing in a step other than Test (Sync deps, native build,
    ...) still needs a ceiling -- MUST-FIRE in spirit: any unbounded step
    is now bounded by this job-level cap."""

    def test_build_job_declares_timeout_minutes(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        build_job = workflow["jobs"]["build"]
        assert "timeout-minutes" in build_job, (
            "build job has no timeout-minutes -- a hang anywhere in it "
            "can run for GitHub's own default ceiling (6 hours) before "
            "anyone notices, exactly the T-3192 failure mode"
        )
        # Comfortably above the slowest OBSERVED full-job completion but
        # well under GitHub's 6-hour default -- a genuine hang still gets
        # caught. T-3748 had raised the ceiling to accommodate ubuntu's
        # (since-reverted, T-3756) combined coverage+test run; the job
        # timeout stays at its existing value, well within this 180m guard.
        assert 0 < build_job["timeout-minutes"] <= 180


# frob:ticket T-3192
class TestUbuntuTestStepIsTimedWithStackDump:
    """The ubuntu-specific Test step must (a) be time-bounded independent
    of the job-level backstop, (b) signal via ABRT (not the default
    SIGTERM `timeout` would otherwise send) so Python's fault handler can
    intercept it, and (c) enable PYTHONFAULTHANDLER so that interception
    actually dumps a stack instead of the process just dying silently."""

    def _ubuntu_test_step(self) -> dict:
        # T-4274: delegates to the shared `_pytest_test_step` lookup
        # (DUP001 extraction -- this used to independently re-derive the
        # same "find the pytest-invoking step for this platform" logic
        # `TestMacosTestStepSignalsTheRealInterpreter._macos_test_step`
        # also needed); still asserts the ABRT-specific detail this
        # class's own tests actually verify.
        step = _pytest_test_step("Test (ubuntu")
        assert "timeout" in step["run"] and "ABRT" in step["run"], (
            "no pytest-invoking step uses `timeout -s ABRT` -- a hang here "
            "still produces no failure signal beyond the job-level backstop, "
            "and none of the stack-dump-on-hang behavior T-3192 exists for"
        )
        return step

    def test_ubuntu_test_step_wraps_pytest_in_timeout_abrt(self) -> None:
        # frob:tests .github/workflows/ci.yml
        step = self._ubuntu_test_step()
        assert "timeout -s ABRT" in step["run"]
        assert "pytest" in step["run"]

    def test_ubuntu_test_step_enables_faulthandler(self) -> None:
        # frob:tests .github/workflows/ci.yml
        step = self._ubuntu_test_step()
        env = step.get("env", {})
        assert env.get("PYTHONFAULTHANDLER") == "1", (
            "timeout -s ABRT sends SIGABRT, but without PYTHONFAULTHANDLER=1 "
            "Python's fault handler never intercepts it to dump a stack -- "
            "the hang still turns into a bare timeout message, not a named "
            "wedge location"
        )

    def test_ubuntu_test_step_only_applies_on_linux(self) -> None:
        """`timeout` is GNU coreutils, absent from Windows' default pwsh
        shell and from macOS's BSD userland -- this step must be gated to
        the platform it actually targets, never applied unconditionally
        across the whole matrix."""
        # frob:tests .github/workflows/ci.yml
        step = self._ubuntu_test_step()
        condition = step.get("if", "")
        assert "Linux" in condition or "ubuntu" in condition.lower()

    def test_a_non_gated_pytest_step_still_exists_for_other_platforms(self) -> None:
        """Windows/macOS must still run the suite -- this guard is
        additive for ubuntu, not a replacement that silently drops
        coverage on the other two platforms."""
        # frob:tests .github/workflows/ci.yml
        pytest_steps = _all_pytest_steps()
        assert len(pytest_steps) >= 2, (
            "expected at least two pytest-invoking steps (ubuntu-timed + "
            "windows/macos-plain) -- found fewer, so a platform may have "
            "silently lost its Test step"
        )


# frob:ticket T-4274
class TestMacosTestStepSignalsTheRealInterpreter:
    """T-4274: the macOS step's stack-dump-on-hang mechanism sends
    `kill -ABRT` to `$!` right after backgrounding the pytest invocation.
    `uv run <cmd>` forks and supervises a real child process rather than
    exec'ing into it (measured directly, see the step's own T-4274 inline
    comment), so `$!` after `uv run pytest ... &` is `uv`'s OWN pid --
    aborting it produces "Aborted (core dumped)"/exit 134 with no
    `PYTHONFAULTHANDLER` stack at all, exactly this ticket's incident.
    These lock the fix: the step must background the venv's own
    interpreter directly, never `uv run`, so `$!` is the real process
    that has `PYTHONFAULTHANDLER=1` installed."""

    def _macos_test_step(self) -> dict:
        return _pytest_test_step("Test (macos")

    def test_macos_step_backgrounds_the_interpreter_directly_not_uv_run(
        self,
    ) -> None:
        # frob:tests .github/workflows/ci.yml
        step = _pytest_test_step("Test (macos")
        run = step["run"]
        assert "pid=$!" in run, (
            "macOS step no longer captures a pid via $! at all -- the "
            "ABRT-for-a-stack-dump mechanism has nothing to target"
        )
        # The line that backgrounds the pytest invocation (ends in `&`,
        # feeds `/tmp/pytest-macos.log`) must invoke the interpreter
        # DIRECTLY -- `uv run pytest` on that exact line is the T-4274
        # regression: `$!` would then be `uv`'s pid, not pytest's.
        backgrounding_lines = [
            line
            for line in run.splitlines()
            if "pytest-macos.log" in line and line.rstrip().endswith("&")
        ]
        assert backgrounding_lines, (
            "no line backgrounds a pytest invocation into pytest-macos.log"
        )
        assert not any("uv run pytest" in line for line in backgrounding_lines), (
            "macOS step backgrounds `uv run pytest` directly -- `$!` right "
            "after this is `uv`'s own pid, not the real pytest/python "
            "process's, so `kill -ABRT \"$pid\"` below aborts `uv` (which "
            "has no PYTHONFAULTHANDLER) instead of the interpreter that "
            "does; this is the exact T-4274 regression -- background the "
            "venv's own interpreter directly (e.g. `.venv/bin/python -m "
            "pytest`) instead"
        )

    def test_macos_step_reports_its_own_margin_on_completion(self) -> None:
        """T-4274 acceptance [3]: the margin between actual duration and
        budget must be visible on every completion, not discovered only
        after a near-miss becomes a failure."""
        # frob:tests .github/workflows/ci.yml
        step = self._macos_test_step()
        run = step["run"]
        assert "started=$(date +%s)" in run, (
            "macOS step never records a start time -- it cannot report "
            "how close a passing run came to its own budget"
        )
        assert "::notice::" in run and "margin" in run, (
            "macOS step never emits a margin notice -- a run finishing "
            "with almost no budget left (as measured before this "
            "ticket's own incident) is invisible until it becomes the "
            "next failure"
        )
