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

from frob.process.parsers.common import Diagnostic, Severity, ToolResult

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


# frob:doc docs/process.md#public-api
def parse_ty(stdout: str, exit_code: int = 0) -> ToolResult:
    diagnostics: list[Diagnostic] = []
    summary_override: str | None = None

    lines = [_ANSI.sub("", ln) for ln in stdout.splitlines()]

    # Pending block-format diagnostic (header parsed, waiting for --> line)
    pending: tuple[str, str, str] | None = None  # (severity, code, message)

    for line in lines:
        stripped = line.strip()

        m3 = _SUMMARY_LINE.match(stripped)
        if m3:
            summary_override = stripped
            pending = None
            continue

        # Try block header
        mh = _BLOCK_HEADER.match(stripped)
        if mh:
            pending = (mh.group(1), mh.group(2), mh.group(3))
            continue

        # Try block location line
        if pending is not None:
            ml = _BLOCK_LOC.match(line)
            if ml:
                severity_str, code, msg = pending
                diagnostics.append(
                    Diagnostic(
                        file=ml.group(1),
                        line=int(ml.group(2)),
                        col=int(ml.group(3)),
                        severity=_severity(severity_str),
                        code=code,
                        message=msg.strip(),
                    )
                )
                pending = None
                continue
            # Non-location continuation line — keep pending until we see -->
            continue

        # Old single-line format
        m = _DIAG_LINE.match(stripped)
        if m:
            severity_str, code, file, row, col, msg = m.groups()
            diagnostics.append(
                Diagnostic(
                    file=file,
                    line=int(row),
                    col=int(col),
                    severity=_severity(severity_str),
                    code=code,
                    message=msg.strip(),
                )
            )
            continue

        m2 = _DIAG_LINE_SIMPLE.match(stripped)
        if m2:
            severity_str, file, row, col, msg = m2.groups()
            diagnostics.append(
                Diagnostic(
                    file=file,
                    line=int(row),
                    col=int(col),
                    severity=_severity(severity_str),
                    message=msg.strip(),
                )
            )
            continue

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")

    if summary_override:
        summary = summary_override
    elif errors or warnings:
        summary = f"{errors} errors, {warnings} warnings"
    else:
        summary = "no issues"

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
