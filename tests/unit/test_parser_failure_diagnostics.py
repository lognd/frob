"""T-2537: no parser may report a failed/unparsable run as an empty
diagnostic list -- that shape is indistinguishable from a clean run.

Both directions are asserted here: a parse failure must be LOUD, and a
genuinely clean run (plus a legitimate warning-only nonzero exit) must be
completely unchanged.
"""

from __future__ import annotations

import json

from frob.app.ticket_runner._verify import _incomplete_tool_results
from frob.process.parsers.cargo import parse_cargo
from frob.process.parsers.common import tool_no_output_result, tool_parse_failure_result
from frob.process.parsers.eslint import parse_eslint
from frob.process.parsers.junit import parse_junit_xml
from frob.process.parsers.ruff import parse_ruff, parse_ruff_json
from frob.process.parsers.valgrind import parse_valgrind

_TRUNCATED_JSON = '[{"filename": "a.py", "code": "E501", "mess'


def _as_result_dict(result) -> dict:
    """The ToolResult as `frob check --json` would emit it, for the
    consumer-side guard to read."""
    return json.loads(result.as_json())


class TestParseFailureResult:
    def test_attaches_error_diagnostic(self) -> None:
        r = tool_parse_failure_result("mytool", "malformed JSON: boom")
        assert r.exit_code == 1
        assert r.error_count == 1
        assert "malformed JSON: boom" in r.diagnostics[0].message

    def test_never_reports_a_zero_exit_code(self) -> None:
        r = tool_parse_failure_result("mytool", "bad", exit_code=0)
        assert r.exit_code == 1


class TestUnparsableOutputIsLoud:
    def test_ruff_malformed_json(self) -> None:
        r = parse_ruff_json(_TRUNCATED_JSON, exit_code=1)
        assert r.exit_code != 0
        assert r.diagnostics, "a failed ruff parse must not report zero diagnostics"
        assert r.error_count >= 1

    def test_ruff_autodetect_malformed_json(self) -> None:
        r = parse_ruff(_TRUNCATED_JSON, exit_code=1)
        assert r.diagnostics

    def test_eslint_malformed_json(self) -> None:
        r = parse_eslint(_TRUNCATED_JSON, exit_code=1)
        assert r.exit_code != 0
        assert r.error_count >= 1

    def test_junit_malformed_xml(self) -> None:
        r = parse_junit_xml("<testsuite><testcase name='a'>")
        assert r.exit_code != 0
        assert r.error_count >= 1

    def test_valgrind_malformed_xml(self) -> None:
        r = parse_valgrind("<?xml version='1.0'?><valgrindoutput><error>", 0)
        assert r.exit_code != 0
        assert r.error_count >= 1

    def test_cargo_malformed_json_line(self) -> None:
        r = parse_cargo('{"reason": "compiler-message", "mess', exit_code=1)
        assert r.error_count >= 1

    def test_consumer_guard_no_longer_sees_a_silent_failure(self) -> None:
        """The T-2521 consumer guard must find nothing to flag now that the
        producer speaks up (the guard itself stays -- defence in depth)."""
        payload = _as_result_dict(parse_ruff_json(_TRUNCATED_JSON, exit_code=1))
        assert _incomplete_tool_results([payload]) == []


class TestNoOutputResult:
    """`tool_no_output_result` (T-4308): a tool that produced NO stdout at
    all is a distinct failure shape from `tool_parse_failure_result`'s
    "produced something unparsable" -- conflating the two (feeding empty
    stdout into a JSON parser and reporting the resulting
    `JSONDecodeError` as "malformed JSON") sends a debugging reader
    auditing the wrong end of the pipeline."""

    def test_attaches_error(self) -> None:
        r = tool_no_output_result("mytool")
        assert r.exit_code == 1
        assert r.error_count == 1
        assert "did not run" in r.diagnostics[0].message
        assert "malformed json" not in r.diagnostics[0].message.lower()

    def test_never_reports_a_zero_exit_code(self) -> None:
        r = tool_no_output_result("mytool", exit_code=0)
        assert r.exit_code == 1


class TestRuffEmptyOutputIsNotMalformed:
    """T-4308: `parse_ruff_json` on truly empty stdout (ruff never ran --
    e.g. `uv run --project <target> ruff ...` failed to spawn the binary,
    the macOS CI root cause) must report "produced no output", never
    "malformed JSON" -- the JSONDecodeError text an empty string produces
    reads identically to a truncated real report, and this project has
    been bitten before by exactly that kind of absent-measurement-in-a-
    bad-measurement's-costume bug."""

    def test_empty_stdout_is_no_output_not_malformed(self) -> None:
        r = parse_ruff_json("", exit_code=2)
        assert r.exit_code != 0
        assert r.error_count >= 1
        assert "did not run" in r.diagnostics[0].message
        assert "malformed json" not in r.diagnostics[0].message.lower()

    def test_whitespace_only_stdout_is_no_output_not_malformed(self) -> None:
        r = parse_ruff_json("   \n", exit_code=2)
        assert "did not run" in r.diagnostics[0].message

    def test_truncated_json_is_still_reported_as_malformed(self) -> None:
        # Regression guard: genuinely unparsable NON-empty output must keep
        # going through the original malformed-JSON path.
        r = parse_ruff_json(_TRUNCATED_JSON, exit_code=1)
        assert "malformed JSON" in r.diagnostics[0].message


class TestCleanRunsAreUnchanged:
    def test_ruff_clean_run(self) -> None:
        r = parse_ruff_json("[]", exit_code=0)
        assert r.exit_code == 0
        assert r.diagnostics == []

    def test_eslint_clean_run(self) -> None:
        r = parse_eslint("[]", exit_code=0)
        assert r.exit_code == 0
        assert r.diagnostics == []

    def test_eslint_empty_output(self) -> None:
        r = parse_eslint("", exit_code=0)
        assert r.exit_code == 0
        assert r.diagnostics == []

    def test_cargo_well_formed_non_compiler_message_is_not_a_failure(self) -> None:
        r = parse_cargo('{"reason": "compiler-artifact"}', exit_code=0)
        assert r.diagnostics == []

    def test_valgrind_clean_xml(self) -> None:
        r = parse_valgrind("<?xml version='1.0'?><valgrindoutput></valgrindoutput>", 0)
        assert r.exit_code == 0
        assert r.diagnostics == []

    def test_junit_clean_xml(self) -> None:
        xml = "<testsuite name='s'><testcase name='a' time='0.1'/></testsuite>"
        r = parse_junit_xml(xml)
        assert r.exit_code == 0
        assert r.diagnostics == []

    def test_warning_only_nonzero_exit_is_not_a_crash(self) -> None:
        """ruff's warning-only findings exit nonzero legitimately; they must
        keep their real diagnostics and never be rewritten as a parse
        failure (T-2521's downstream special case)."""
        payload = json.dumps(
            [
                {
                    "filename": "a.py",
                    "code": "W291",
                    "message": "trailing whitespace",
                    "location": {"row": 1, "column": 1},
                }
            ]
        )
        r = parse_ruff_json(payload, exit_code=1)
        assert r.exit_code == 1
        assert r.warning_count == 1
        assert r.error_count == 0
        assert _incomplete_tool_results([_as_result_dict(r)]) == []
