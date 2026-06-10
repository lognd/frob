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
    parse_clang,
    parse_junit_xml,
    parse_pycharm_dir,
    parse_pytest,
    parse_ruff,
    parse_ty,
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
}


def run(cfg: AppConfig) -> None:
    tool = cfg.parse_tool
    if tool is None:
        _log.error("frob parse requires <tool>")
        sys.exit(1)

    _ALL_TOOLS = set(_PARSERS) | {"pycharm"}
    if tool not in _ALL_TOOLS:
        known = ", ".join(sorted(_ALL_TOOLS))
        _log.error("unknown tool %r -- known: %s", tool, known)
        sys.exit(1)

    # pycharm takes a directory, not stdin
    if tool == "pycharm":
        if cfg.parse_input is None:
            _log.error("frob parse pycharm requires a directory argument")
            sys.exit(1)
        d = cfg.parse_input
        if not d.is_dir():
            _log.error("frob parse pycharm: %s is not a directory", d)
            sys.exit(1)
        result = parse_pycharm_dir(d)
    else:
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
