"""
ty (Astral's type checker) output parser.

ty outputs multi-line diagnostic blocks:
  error[<code>]: <message>
    --> file.py:<line>:<col>

or the older single-line format:
  error[<code>] file.py:<line>:<col>: <message>
"""

# frob:waive TEST005 reason="module line coverage 77.8%, debt T-0160"

from __future__ import annotations

import re
from typing import cast

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


# frob:doc docs/modules/process.md#public-api
def parse_ty(stdout: str, exit_code: int = 0) -> ToolResult:
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
