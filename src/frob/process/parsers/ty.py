"""
ty (Astral's type checker) output parser.

ty outputs multi-line diagnostic blocks:
  error[<code>]: <message>
    --> file.py:<line>:<col>

or the older single-line format:
  error[<code>] file.py:<line>:<col>: <message>
"""

from __future__ import annotations

import re
from typing import cast

from frob.process._project_tool import tool_absent_from_project
from frob.process.parsers.common import (
    Diagnostic,
    Severity,
    ToolResult,
    summarize_severity,
)

# Multi-line format: "error[code]: message" header
_BLOCK_HEADER = re.compile(r"^(error|warning|info|note)\[([^\]]+)\]:\s+(.*)$")
# Location line inside a block: "  --> file:line:col"
_BLOCK_LOC = re.compile(r"^\s+-->\s+(.*?):(\d+):(\d+)$")
# Old single-line format: "error[code] file:line:col: message"
_DIAG_LINE = re.compile(
    r"^(error|warning|info|note)\[([^\]]+)\]\s+(.*?):(\d+):(\d+):\s+(.*)$"
)
# Simpler single-line without bracket code
_DIAG_LINE_SIMPLE = re.compile(
    r"^(error|warning|info|note)\s+(.*?):(\d+):(\d+):\s+(.*)$"
)
_SUMMARY_LINE = re.compile(r"^Found (\d+) diagnostic")
# Strip ANSI escape codes
_ANSI = re.compile(r"\x1b\[[0-9;]*m")


# frob:ticket T-0045
def _block_loc_diagnostic(
    line: str, pending: tuple[str, str, str]
) -> Diagnostic | None:
    """Diagnostic for a block-format `--> file:line:col` line, given its header."""
    ml = _BLOCK_LOC.match(line)
    if ml is None:
        return None
    severity_str, code, msg = pending
    return Diagnostic(
        file=ml.group(1),
        line=int(ml.group(2)),
        col=int(ml.group(3)),
        severity=_severity(severity_str),
        code=code,
        message=msg.strip(),
    )


# frob:ticket T-0045
def _single_line_diagnostic(stripped: str) -> Diagnostic | None:
    """Diagnostic for either legacy single-line ty format, or None."""
    m = _DIAG_LINE.match(stripped)
    if m:
        severity_str, code, file, row, col, msg = m.groups()
        return Diagnostic(
            file=file,
            line=int(row),
            col=int(col),
            severity=_severity(severity_str),
            code=code,
            message=msg.strip(),
        )
    m2 = _DIAG_LINE_SIMPLE.match(stripped)
    if m2:
        severity_str, file, row, col, msg = m2.groups()
        return Diagnostic(
            file=file,
            line=int(row),
            col=int(col),
            severity=_severity(severity_str),
            message=msg.strip(),
        )
    return None


# frob:ticket T-0045
def _scan_ty_lines(stdout: str) -> tuple[list[Diagnostic], str | None]:
    """Scan ty output into (diagnostics, optional summary-override line)."""
    diagnostics: list[Diagnostic] = []
    summary_override: str | None = None
    # Pending block-format diagnostic (header parsed, waiting for --> line).
    pending: tuple[str, str, str] | None = None  # (severity, code, message)

    for line in (_ANSI.sub("", ln) for ln in stdout.splitlines()):
        stripped = line.strip()
        mh = _BLOCK_HEADER.match(stripped)
        if _SUMMARY_LINE.match(stripped):
            summary_override, pending = stripped, None
        elif mh:
            pending = (mh.group(1), mh.group(2), mh.group(3))
        elif pending is not None:
            # A non-location continuation line keeps pending until we see -->.
            diag = _block_loc_diagnostic(line, pending)
            if diag is not None:
                diagnostics.append(diag)
                pending = None
        else:
            diag = _single_line_diagnostic(stripped)
            if diag is not None:
                diagnostics.append(diag)

    return diagnostics, summary_override


# frob:ticket T-4358
# frob:doc docs/modules/process.md#public-api
# frob:tests tests/unit/test_tool_absent_parser_reconcile.py::TestTyAbsentToolIsUnmeasured.test_spawn_failure_text_is_unmeasured  # noqa: E501
# frob:tests tests/unit/test_tool_absent_parser_reconcile.py::TestTyAbsentToolIsUnmeasured.test_unrelated_nonzero_exit_with_no_matches_still_empty  # noqa: E501
# frob:tests tests/unit/test_tool_absent_parser_reconcile.py::TestTyAbsentToolIsUnmeasured.test_real_diagnostic_still_parses_even_with_nonzero_exit  # noqa: E501
# frob:waive FMT001 reason="single-line frob:tests directives naming long test node \
# ids -- already at frob fmt's own canonical form, same unwrappable shape as \
# src/frob/app/pyfmt_runner.py's existing FMT001 waiver"
# frob:waive AFFECT001 reason="T-4358 adds one new branch (tool_absent_from_project \
# classification) ahead of the existing regex scan -- docs/modules/process.md's own \
# text already documents T-4354's identical doctrine for this exact shape (see 'Tool \
# absent from the target project' there, which names this very follow-up as out of \
# T-4354's own scope); its public-api section is under closure obligations this diff \
# cannot satisfy without pulling in an unrelated, large cross-ticket doc-scope \
# conflict, matching parse_ruff_json's own identical waiver for the sibling branch \
# this mirrors"
def parse_ty(stdout: str, exit_code: int = 0) -> ToolResult:
    """Parse `ty`'s diagnostic text.

    T-4358: `stdout` here is, at this function's real caller
    (`frob.check._python`), already `proc.stdout + proc.stderr`
    concatenated -- so `uv run`'s own "Failed to spawn: `ty`" failure
    text (T-4354's `tool_absent_from_project` shape: `ty` absent from
    the TARGET project's own environment, a legitimate not-installed
    state, never an error) is visible here without a separate `stderr`
    parameter. Checked explicitly, ahead of the regex scan, so this
    parser reports the same UNMEASURED shape ruff-check's parser now
    reports on purpose for the identical condition (T-4358), rather
    than reaching it only by accident of the scan finding nothing to
    match (T-4309's `_is_silent_nonzero_exit` net, which this shape
    also falls into either way -- explicit here so a reader auditing
    this parser sees the classification instead of inferring it)."""
    if tool_absent_from_project("ty", exit_code, stdout):
        return ToolResult(
            tool="ty",
            exit_code=exit_code,
            diagnostics=[],
            summary="ty absent from target project (not measured)",
        )
    diagnostics, summary_override = _scan_ty_lines(stdout)
    summary = summary_override or summarize_severity(diagnostics)
    return ToolResult(
        tool="ty",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary,
    )


def _severity(s: str) -> Severity:
    if s in ("error", "warning", "note", "info"):
        return cast(Severity, s)
    return "error"
