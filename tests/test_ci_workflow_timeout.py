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
        # Comfortably above the slowest OBSERVED full-job completion
        # (macOS's ~23-minute Test stage, run 33135896391) but well under
        # GitHub's 6-hour default -- a genuine hang still gets caught.
        assert 0 < build_job["timeout-minutes"] <= 120


# frob:ticket T-3192
class TestUbuntuTestStepIsTimedWithStackDump:
    """The ubuntu-specific Test step must (a) be time-bounded independent
    of the job-level backstop, (b) signal via ABRT (not the default
    SIGTERM `timeout` would otherwise send) so Python's fault handler can
    intercept it, and (c) enable PYTHONFAULTHANDLER so that interception
    actually dumps a stack instead of the process just dying silently."""

    def _ubuntu_test_step(self) -> dict:
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        candidates = [
            s for s in steps if isinstance(s.get("run"), str) and "pytest" in s["run"]
        ]
        assert candidates, "no step invokes pytest at all"
        ubuntu_steps = [
            s for s in candidates if "timeout" in s["run"] and "ABRT" in s["run"]
        ]
        assert ubuntu_steps, (
            "no pytest-invoking step uses `timeout -s ABRT` -- a hang here "
            "still produces no failure signal beyond the job-level backstop, "
            "and none of the stack-dump-on-hang behavior T-3192 exists for"
        )
        return ubuntu_steps[0]

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
        workflow = _load_ci_workflow()
        steps = workflow["jobs"]["build"]["steps"]
        pytest_steps = [
            s for s in steps if isinstance(s.get("run"), str) and "pytest" in s["run"]
        ]
        assert len(pytest_steps) >= 2, (
            "expected at least two pytest-invoking steps (ubuntu-timed + "
            "windows/macos-plain) -- found fewer, so a platform may have "
            "silently lost its Test step"
        )
