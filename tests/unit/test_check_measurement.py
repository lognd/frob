"""T-2391: `CheckResult.unmeasured_results` and the `as_text` "## Unmeasured
gates" roster -- the fail-loudly doctrine's "print automatically, never a
second command to remember" directive applied to gate-measurement status."""

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


class TestUnmeasuredResults:
    """`CheckResult.unmeasured_results` -- the roster both `as_text` and a
    `--json` consumer can read without re-deriving the predicate."""

    def test_empty_when_every_result_measured(self) -> None:
        # frob:tests tests/unit/test_check_measurement.py::TestUnmeasuredResults.test_empty_when_every_result_measured  # noqa: E501
        result = CheckResult(
            path=".", results=[_measured("gate:COV"), _measured("ruff-check")]
        )
        assert result.unmeasured_results == []

    def test_lists_every_not_measured_result(self) -> None:
        # frob:tests tests/unit/test_check_measurement.py::TestUnmeasuredResults.test_lists_every_not_measured_result  # noqa: E501
        not_measured = _not_measured("gate:FLAGCOV", "no commands declared")
        result = CheckResult(path=".", results=[_measured("gate:COV"), not_measured])
        assert result.unmeasured_results == [not_measured]


class TestAsTextUnmeasuredSection:
    """`as_text` prints the roster automatically whenever it is non-empty,
    and omits the section entirely otherwise (T-2391: never a silent gap,
    never noise on a genuinely clean run)."""

    def test_section_absent_when_everything_measured(self) -> None:
        # frob:tests tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection.test_section_absent_when_everything_measured  # noqa: E501
        result = CheckResult(path=".", results=[_measured("gate:COV")])
        assert "Unmeasured gates" not in result.as_text()

    def test_section_present_and_names_the_gate_and_reason(self) -> None:
        # frob:tests tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection.test_section_present_and_names_the_gate_and_reason  # noqa: E501
        result = CheckResult(
            path=".",
            results=[_not_measured("gate:FLAGCOV", "no commands declared")],
        )
        text = result.as_text()
        assert "Unmeasured gates" in text
        assert "gate:FLAGCOV" in text
        assert "no commands declared" in text

    def test_json_exposes_measurement_without_a_dedicated_key(self) -> None:
        # frob:tests tests/unit/test_check_measurement.py::TestAsTextUnmeasuredSection.test_json_exposes_measurement_without_a_dedicated_key  # noqa: E501
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
