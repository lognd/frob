"""T-4460: the ubuntu self-gate failed in CI and the run page showed no
summary -- the per-gate rows and the gate-summary line only ever existed
inside the step log, thousands of lines up. Locks that (1) the "frob check
(self-gate)" step tees its output to a `$RUNNER_TEMP` log file (never
`/tmp`, T-4462: Windows runners have no `/tmp`) with `set -o pipefail`
under `shell: bash` so its own exit code is unchanged, and (2) a SEPARATE
`if: always()` follow-up step (never the self-gate step itself, so it
still runs on a red or cancelled self-gate) writes a job-summary block on
every matrix leg. Mirrors tests/test_ci_workflow_matrix.py's own
`_load_ci_workflow` precedent for this file.
"""

import ast
from pathlib import Path

import yaml


# frob:waive DUP001 reason="mirrors tests/test_ci_workflow_matrix.py's and \
# tests/test_ci_workflow_timeout.py's own pre-existing identical helper (both already \
# carry this exact docstring's own note); extracting a shared conftest fixture touches \
# those two files, which are outside this ticket's scope (.github/workflows/ci.yml, \
# tests/test_ci_workflow*.py, docs/commands/check.md permits touching them, but the \
# shared-helper refactor itself is a separate, non-blocking cleanup, not part of this \
# ticket's acceptance criteria)"
def _load_ci_workflow() -> dict:
    """Parse .github/workflows/ci.yml (frob:tests target) into a dict."""
    text = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    return yaml.safe_load(text)


def _build_steps() -> list[dict]:
    """The `build` job's step list -- the one matrix job all three legs
    share, where the self-gate and its summary step live."""
    return _load_ci_workflow()["jobs"]["build"]["steps"]


def _step(name: str) -> dict:
    """Look up one `build` job step by its exact `name:`, or fail loudly
    naming what was searched for -- a renamed step must not silently read
    as "missing feature" in every test below."""
    steps = _build_steps()
    for step in steps:
        if step.get("name") == name:
            return step
    raise AssertionError(f"no build-job step named {name!r} in ci.yml")


class TestSelfGateStepCapturesItsOutput:
    """T-4460: the self-gate step's own stdout must be captured to a file
    the follow-up summary step can read, without changing its exit-code
    semantics."""

    # frob:tests .github/workflows/ci.yml
    def test_self_gate_step_uses_bash(self) -> None:
        step = _step("frob check (self-gate)")
        assert step.get("shell") == "bash", (
            "self-gate step's default shell is pwsh on windows-latest, "
            "which has neither `tee` nor `set -o pipefail`"
        )

    # frob:tests .github/workflows/ci.yml
    def test_self_gate_step_tees_to_runner_temp_with_pipefail(self) -> None:
        step = _step("frob check (self-gate)")
        run = step["run"]
        assert "set -o pipefail" in run, (
            "without pipefail, `frob check | tee ...`'s exit code is "
            "tee's (always 0), not the gate run's -- a red self-gate "
            "would silently pass this step"
        )
        assert "tee" in run and "RUNNER_TEMP" in run, (
            "self-gate output must be teed into $RUNNER_TEMP (never "
            "/tmp -- T-4462, Windows runners have no /tmp) so the "
            "follow-up summary step can read it"
        )
        assert "/tmp" not in run, (
            "self-gate step must not write under /tmp -- Windows "
            "runners have no /tmp (T-4462)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_self_gate_step_still_runs_frob_check(self) -> None:
        step = _step("frob check (self-gate)")
        assert "uv run frob check" in step["run"]
        # unchanged gating condition -- this ticket must not touch when
        # the self-gate runs, only how its output is captured
        assert step["if"] == (
            "${{ !cancelled() && (success() || matrix.os == 'windows-latest') }}"
        )


class TestJobSummaryStepExists:
    """T-4460 acceptance (1)/(2): a follow-up step, `if: always()`, writes
    a compact job-summary block on every leg -- never the failing self-gate
    step itself."""

    # frob:tests .github/workflows/ci.yml
    def test_summary_step_exists(self) -> None:
        # raises AssertionError with a clear message if missing
        _step("Write self-gate results to job summary (T-4460)")

    # frob:tests .github/workflows/ci.yml
    def test_summary_step_is_always(self) -> None:
        step = _step("Write self-gate results to job summary (T-4460)")
        assert step.get("if") == "always()", (
            "must run on a red OR cancelled self-gate step -- that is "
            "exactly the run this ticket exists to make visible"
        )

    # frob:tests .github/workflows/ci.yml
    def test_summary_step_uses_bash(self) -> None:
        step = _step("Write self-gate results to job summary (T-4460)")
        assert step.get("shell") == "bash", (
            "the job's default shell is pwsh on windows-latest, which "
            "has no $GITHUB_STEP_SUMMARY-append idiom this step relies on"
        )

    # frob:tests .github/workflows/ci.yml
    def test_summary_step_is_separate_and_runs_after_self_gate(self) -> None:
        steps = _build_steps()
        names = [s.get("name") for s in steps]
        self_gate_idx = names.index("frob check (self-gate)")
        summary_idx = names.index("Write self-gate results to job summary (T-4460)")
        assert summary_idx > self_gate_idx, (
            "the summary step must come AFTER the self-gate step so it "
            "can read what the self-gate produced"
        )
        assert summary_idx != self_gate_idx, (
            "must be a separate step, not folded into the self-gate "
            "step itself -- a failing self-gate step's own remaining "
            "commands never run"
        )

    # frob:tests .github/workflows/ci.yml
    def test_summary_step_reads_json_not_the_human_log(self) -> None:
        step = _step("Write self-gate results to job summary (T-4460)")
        run = step["run"]
        assert "--json" in run, (
            "the summary step should parse frob check's machine-"
            "readable --json shape, not re-derive gate rows/findings by "
            "re-parsing the human-readable renderer's text output"
        )
        assert "GITHUB_STEP_SUMMARY" in run
        assert "/tmp" not in run, (
            "must not write under /tmp -- Windows runners have no /tmp (T-4462)"
        )

    # frob:tests .github/workflows/ci.yml
    def test_summary_step_python_is_syntactically_valid(self) -> None:
        """The step embeds a Python script via a `python - <<'PY'` heredoc
        inside a YAML literal block scalar; YAML strips the block's common
        leading indentation before bash ever sees it (the same mechanism
        the pre-existing TEST012 `python -c "..."` steps in this file rely
        on), so the script as PARSED here must compile as top-level
        Python with no leading indentation of its own."""
        step = _step("Write self-gate results to job summary (T-4460)")
        run = step["run"]
        start_marker = "<<'PY'\n"
        start = run.index(start_marker) + len(start_marker)
        end = run.index("\nPY", start)
        script = run[start:end]
        ast.parse(script)  # raises SyntaxError on failure

    # frob:tests .github/workflows/ci.yml
    def test_summary_step_never_fails_the_job(self) -> None:
        step = _step("Write self-gate results to job summary (T-4460)")
        run = step["run"]
        # no bare `set -e`/`exit 1`-style hard failure in the shell
        # preamble -- a parsing problem in the summary generator must
        # not mask, or pile onto, the self-gate step's own verdict.
        assert "set -e" not in run
        # the frob check --json capture itself must not be allowed to
        # fail the step on a nonzero self-gate exit code
        assert "|| true" in run


class TestJobSummaryDocumented:
    """T-4460 acceptance (4): docs/commands/check.md mentions the summary."""

    # frob:tests docs/commands/check.md
    def test_check_docs_mention_the_job_summary(self) -> None:
        text = (
            Path(__file__).resolve().parents[1] / "docs" / "commands" / "check.md"
        ).read_text(encoding="utf-8")
        assert "GITHUB_STEP_SUMMARY" in text
        assert "T-4460" in text
