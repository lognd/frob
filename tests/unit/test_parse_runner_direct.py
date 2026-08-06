"""Direct-call coverage for `frob.app.parse_runner.run` (T-0160 TEST005 batch 10).

`tests/unit/test_parse.py` exercises `frob parse` via subprocess (end-to-end,
but subprocess calls do not attribute back to this module's own coverage).
This file calls `run(cfg)` in-process to drive every branch: no tool, unknown
tool, file-read OSError, stdin fallback, json vs text output, and the
passthrough exit-code branch.
"""


from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.parse_runner import run


class TestParseRunnerRun:
    def test_missing_tool_exits_with_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_missing_tool_exits_with_error  # noqa: E501
        caplog.set_level(logging.ERROR)
        cfg = AppConfig(parse_tool=None)
        with pytest.raises(SystemExit):
            run(cfg)
        assert "requires <tool>" in caplog.text

    def test_unknown_tool_exits_with_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_unknown_tool_exits_with_error  # noqa: E501
        caplog.set_level(logging.ERROR)
        cfg = AppConfig(parse_tool="not-a-real-tool")
        with pytest.raises(SystemExit):
            run(cfg)
        assert "unknown tool" in caplog.text

    def test_unreadable_file_exits_with_error(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_unreadable_file_exits_with_error  # noqa: E501
        caplog.set_level(logging.ERROR)
        missing = tmp_path / "does-not-exist.txt"
        cfg = AppConfig(parse_tool="ruff", parse_input=missing)
        with pytest.raises(SystemExit):
            run(cfg)
        assert "cannot read" in caplog.text

    def test_reads_from_file_and_logs_text(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_reads_from_file_and_logs_text  # noqa: E501
        caplog.set_level(logging.INFO)
        src = tmp_path / "ruff_output.txt"
        src.write_text("All checks passed!\n")
        cfg = AppConfig(
            parse_tool="ruff", parse_input=src, parse_exit_code=0, parse_json=False
        )
        run(cfg)
        assert caplog.text.strip()

    def test_reads_from_stdin_and_logs_json(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_reads_from_stdin_and_logs_json  # noqa: E501
        import io

        caplog.set_level(logging.INFO)
        monkeypatch.setattr("sys.stdin", io.StringIO("All checks passed!\n"))
        cfg = AppConfig(
            parse_tool="ruff", parse_input=None, parse_exit_code=0, parse_json=True
        )
        run(cfg)
        assert '"' in caplog.text  # json output, not the plain-text summary

    def test_passthrough_propagates_failing_exit_code(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_passthrough_propagates_failing_exit_code  # noqa: E501
        src = tmp_path / "ruff_output.txt"
        src.write_text("some_file.py:1:1: E501 line too long\nFound 1 error.\n")
        cfg = AppConfig(
            parse_tool="ruff",
            parse_input=src,
            parse_exit_code=1,
            parse_passthrough=True,
        )
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code != 0

    def test_no_passthrough_does_not_exit_on_failure(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_no_passthrough_does_not_exit_on_failure  # noqa: E501
        src = tmp_path / "ruff_output.txt"
        src.write_text("some_file.py:1:1: E501 line too long\nFound 1 error.\n")
        cfg = AppConfig(
            parse_tool="ruff",
            parse_input=src,
            parse_exit_code=1,
            parse_passthrough=False,
        )
        run(cfg)  # must not raise
