"""T-2391: `CheckResult.unmeasured_results` and the `as_text` "## Unmeasured
gates" roster -- the fail-loudly doctrine's "print automatically, never a
second command to remember" directive applied to gate-measurement status.

T-4309 adds the sibling shape: a `ToolResult` whose process exited nonzero
but carries zero diagnostics (`_is_silent_nonzero_exit`) -- MEASURED live on
the macOS leg of a CI run, where `ty` and `ruff-format` each rendered `FAIL`
with a detail string that said nothing was wrong ("no issues" / "0 files
would be reformatted"). Routed into the same UNRES vocabulary as the T-2391
gate case rather than left to manufacture a FAIL."""

from __future__ import annotations

from frob.check import CheckResult
from frob.process.parsers.common import Diagnostic, ToolResult


def _measured(tool: str) -> ToolResult:
    return ToolResult(tool=tool, diagnostics=[], summary="0 errors, 0 warnings")


def _not_measured(tool: str, reason: str) -> ToolResult:
    return ToolResult(
        tool=tool,
        diagnostics=[Diagnostic(severity="info", message=reason)],
        summary="0 errors, 0 warnings, 1 unresolved, 0 waived",
    )


# frob:ticket T-4309
def _silent_nonzero_exit(tool: str, summary: str) -> ToolResult:
    """A `ToolResult` shaped like T-4309's observed `ty`/`ruff-format`
    macOS rows: nonzero exit code, zero diagnostics, and a summary that
    reads as clean."""
    return ToolResult(tool=tool, exit_code=1, diagnostics=[], summary=summary)


class TestUnmeasuredResults:
    """`CheckResult.unmeasured_results` -- the roster both `as_text` and a
    `--json` consumer can read without re-deriving the predicate."""

    def test_empty_when_every_result_measured(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestUnmeasuredResults.test_empty_when_e\
        # very_result_measured
        result = CheckResult(
            path=".", results=[_measured("gate:COV"), _measured("ruff-check")]
        )
        assert result.unmeasured_results == []

    def test_lists_every_not_measured_result(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestUnmeasuredResults.test_lists_every_\
        # not_measured_result
        not_measured = _not_measured("gate:FLAGCOV", "no commands declared")
        result = CheckResult(path=".", results=[_measured("gate:COV"), not_measured])
        assert result.unmeasured_results == [not_measured]


class TestAsTextUnmeasuredSection:
    """`as_text` prints the roster automatically whenever it is non-empty,
    and omits the section entirely otherwise (T-2391: never a silent gap,
    never noise on a genuinely clean run)."""

    def test_section_absent_when_everything_measured(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection.test_sectio\
        # n_absent_when_everything_measured
        result = CheckResult(path=".", results=[_measured("gate:COV")])
        assert "Unmeasured gates" not in result.as_text()

    def test_section_present_and_names_the_gate_and_reason(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection.test_sectio\
        # n_present_and_names_the_gate_and_reason
        result = CheckResult(
            path=".",
            results=[_not_measured("gate:FLAGCOV", "no commands declared")],
        )
        text = result.as_text()
        assert "Unmeasured gates" in text
        assert "gate:FLAGCOV" in text
        assert "no commands declared" in text

    def test_json_exposes_measurement_without_a_dedicated_key(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection.test_json_e\
        # xposes_measurement_without_a_dedicated_key
        # T-2391 acceptance[0]: a --json consumer can find the same
        # information as_text prints, per-result, via ToolResult's own
        # computed fields -- CheckResult.as_json needed no reshape.
        import json

        result = CheckResult(
            path=".",
            results=[_not_measured("gate:FLAGCOV", "no commands declared")],
        )
        dumped = json.loads(result.as_json())
        (r,) = dumped["results"]
        assert r["measurement"] == "not_measured"
        assert r["measurement_reason"] == "no commands declared"


# frob:ticket T-4309
class TestSilentNonzeroExit:
    """T-4309: a nonzero exit with zero diagnostics must never render as a
    manufactured FAIL when its own detail text says nothing is wrong."""

    def test_listed_in_unmeasured_results(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestSilentNonzeroExit.test_listed_in_un\
        # measured_results
        silent = _silent_nonzero_exit("ty", "linux: no issues; darwin: no issues")
        result = CheckResult(path=".", results=[_measured("gate:COV"), silent])
        assert result.unmeasured_results == [silent]

    def test_as_text_renders_unres_not_fail(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestSilentNonzeroExit.test_as_text_rend\
        # ers_unres_not_fail
        result = CheckResult(
            path=".",
            results=[
                _silent_nonzero_exit("ruff-format", "0 files would be reformatted")
            ],
        )
        text = result.as_text()
        assert "UNRES  ruff-format" in text
        assert "FAIL  ruff-format" not in text

    def test_as_text_lists_reason_with_exit_code_and_summary(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestSilentNonzeroExit.test_as_text_list\
        # s_reason_with_exit_code_and_summary
        result = CheckResult(
            path=".",
            results=[_silent_nonzero_exit("ty", "darwin: no issues")],
        )
        text = result.as_text()
        assert "Unmeasured gates" in text
        assert "ty" in text
        assert "exited 1" in text or "exited" in text
        assert "darwin: no issues" in text

    def test_a_real_failure_with_diagnostics_still_renders_fail(self) -> None:
        # frob:tests \
        # tests/unit/test_check_measurement.py::TestSilentNonzeroExit.test_a_real_failu\
        # re_with_diagnostics_still_renders_fail
        # Guardrail: this predicate must never soften a genuine failure --
        # tool_unavailable_result/tool_disabled_result/ruff-check's
        # malformed-JSON error all attach a real error diagnostic, so
        # error_count > 0 and this shape is untouched.
        real_failure = ToolResult(
            tool="ruff-check",
            exit_code=1,
            diagnostics=[
                Diagnostic(severity="error", message="ruff output could not be parsed")
            ],
            summary="ruff output could not be parsed: malformed JSON",
        )
        result = CheckResult(path=".", results=[real_failure])
        text = result.as_text()
        assert "FAIL  ruff-check" in text
        assert result.unmeasured_results == []
