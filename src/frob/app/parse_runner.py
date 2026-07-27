"""
frob parse -- read tool output from stdin or a file and emit a compact summary.

Usage:
    pytest ... 2>&1 | frob parse pytest
    frob parse ruff < ruff_output.txt
    frob parse ty --json < ty_output.txt
    frob parse clang --exit-code 1 < build.log
    frob parse junit < test_results.xml
"""

from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.process.parsers import (
    parse_cargo,
    parse_clang,
    parse_clang_tidy,
    parse_eslint,
    parse_junit_xml,
    parse_pytest,
    parse_ruff,
    parse_tsc,
    parse_ty,
    parse_valgrind,
)

_log = get_logger(__name__)

_PARSERS = {
    "pytest": lambda text, rc: parse_pytest(text, exit_code=rc),
    "ruff": lambda text, rc: parse_ruff(text, exit_code=rc),
    "ty": lambda text, rc: parse_ty(text, exit_code=rc),
    "clang": lambda text, rc: parse_clang(text, exit_code=rc, tool="clang"),
    "clang++": lambda text, rc: parse_clang(text, exit_code=rc, tool="clang++"),
    "gcc": lambda text, rc: parse_clang(text, exit_code=rc, tool="gcc"),
    "g++": lambda text, rc: parse_clang(text, exit_code=rc, tool="g++"),
    "junit": lambda text, rc: parse_junit_xml(text, tool="junit"),
    "gtest": lambda text, rc: parse_junit_xml(text, tool="gtest"),
    "catch2": lambda text, rc: parse_junit_xml(text, tool="catch2"),
    "cargo": lambda text, rc: parse_cargo(text, exit_code=rc),
    "clang-tidy": lambda text, rc: parse_clang_tidy(text, exit_code=rc),
    "valgrind": lambda text, rc: parse_valgrind(text, exit_code=rc),
    "tsc": lambda text, rc: parse_tsc(text, exit_code=rc),
    "eslint": lambda text, rc: parse_eslint(text, exit_code=rc),
}


# frob:doc docs/modules/app.md#runners
# frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_missing_tool_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_unknown_tool_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_unreadable_file_exits_with_error  # noqa: E501
# frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_reads_from_file_and_logs_text  # noqa: E501
# frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_reads_from_stdin_and_logs_json  # noqa: E501
# frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_passthrough_propagates_failing_exit_code  # noqa: E501
# frob:tests tests/unit/test_parse_runner_direct.py::TestParseRunnerRun.test_no_passthrough_does_not_exit_on_failure  # noqa: E501
# frob:waive ARCH103 reason="T-0977: `frob parse` CLI entrypoint -- validates the tool \
# arg, dispatches stdin/file input, logs text or json, propagates the passthrough exit \
# code; this dispatch/format/exit triad IS the runner's job, matching every other \
# `frob.app.*_runner`"
def run(cfg: AppConfig) -> None:
    tool = cfg.parse_tool
    if tool is None:
        _log.error("frob parse requires <tool>")
        sys.exit(1)

    if tool not in _PARSERS:
        known = ", ".join(sorted(_PARSERS))
        _log.error("unknown tool %r -- known: %s", tool, known)
        sys.exit(1)

    # Read from file or stdin
    if cfg.parse_input is not None:
        try:
            text = cfg.parse_input.read_text()
        except OSError as exc:
            _log.error("cannot read %s: %s", cfg.parse_input, exc)
            sys.exit(1)
    else:
        text = sys.stdin.read()
    result = _PARSERS[tool](text, cfg.parse_exit_code)

    if cfg.parse_json:
        _log.info(result.as_json())
    else:
        _log.info(result.as_text(verbose=cfg.parse_verbose))

    # Propagate the tool's exit code so pipelines work correctly
    if cfg.parse_passthrough and not result.passed:
        sys.exit(result.exit_code or 1)
