"""
Valgrind memcheck output parser.

Supports both plain text and XML (--xml=yes) output.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from frob.process.parsers.common import Diagnostic, ToolResult

_ERROR_PAD = re.compile(r"^==\d+==")
_LEAK = re.compile(
    r"(definitely lost|indirectly lost|possibly lost|still reachable):\s*([\d,]+) bytes"
)
_INVALID = re.compile(
    r"(Invalid read|Invalid write|Use of uninitialised|Conditional jump)"
)


def parse_valgrind(stdout: str, exit_code: int = 0) -> ToolResult:
    text = stdout.strip()
    if text.startswith("<?xml") or text.startswith("<valgrindoutput"):
        return _parse_xml(text, exit_code)
    return _parse_text(text, exit_code)


def _parse_text(text: str, exit_code: int) -> ToolResult:
    diagnostics: list[Diagnostic] = []
    lines = text.splitlines()
    # Strip pid prefix ==1234==
    clean = [_ERROR_PAD.sub("", ln).strip() for ln in lines]

    error_blocks: list[list[str]] = []
    current: list[str] = []
    for line in clean:
        if line == "" and current:
            if any(line for line in current):
                error_blocks.append(current)
            current = []
        else:
            current.append(line)

    for block in error_blocks:
        first = block[0] if block else ""
        if _INVALID.search(first) or "Invalid" in first:
            # Find location from "at 0x... (func in file:line)"
            loc_line = next((ln for ln in block if "(" in ln and ":" in ln), None)
            file_ref: str | None = None
            lineno: int | None = None
            if loc_line:
                m = re.search(r"\(.*?:(\d+)\)", loc_line)
                if m:
                    lineno = int(m.group(1))
                fm = re.search(r"\((.*?):(\d+)\)", loc_line)
                if fm:
                    file_ref = fm.group(1)
                    lineno = int(fm.group(2))
            diagnostics.append(
                Diagnostic(
                    file=file_ref,
                    line=lineno,
                    severity="error",
                    message=first[:120],
                )
            )

    # Leak summary
    leak_lines = [ln for ln in clean if _LEAK.search(ln)]
    for ll in leak_lines:
        m = _LEAK.search(ll)
        if m:
            kind, amount = m.groups()
            if kind in ("definitely lost", "indirectly lost"):
                diagnostics.append(
                    Diagnostic(
                        severity="error",
                        message=f"memory leak ({kind}): {amount} bytes",
                    )
                )
            else:
                diagnostics.append(
                    Diagnostic(
                        severity="warning",
                        message=f"memory ({kind}): {amount} bytes",
                    )
                )

    # Summary line
    err_summary = next((ln for ln in clean if "ERROR SUMMARY:" in ln), None)
    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = sum(1 for d in diagnostics if d.severity == "warning")
    summary = err_summary or (
        f"{errors} errors, {warnings} warnings" if errors or warnings else "clean"
    )
    return ToolResult(
        tool="valgrind",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary.strip(),
    )


def _parse_xml(text: str, exit_code: int) -> ToolResult:
    diagnostics: list[Diagnostic] = []
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return ToolResult(
            tool="valgrind", exit_code=exit_code, summary="XML parse error"
        )

    for error in root.findall(".//error"):
        kind = (error.findtext("kind") or "").lower()
        what = error.findtext("what") or error.findtext("xwhat/text") or kind
        sev = "error" if "definite" in kind or "invalid" in kind else "warning"
        # First frame with file info
        file_ref: str | None = None
        lineno: int | None = None
        for frame in error.findall(".//frame"):
            fn = frame.findtext("file")
            ln = frame.findtext("line")
            if fn and ln:
                file_ref = fn
                lineno = int(ln)
                break
        diagnostics.append(
            Diagnostic(
                file=file_ref,
                line=lineno,
                severity=sev,
                message=(what or "")[:120],
            )
        )

    errors = sum(1 for d in diagnostics if d.severity == "error")
    warnings = len(diagnostics) - errors
    summary = f"{errors} errors, {warnings} warnings" if errors or warnings else "clean"
    return ToolResult(
        tool="valgrind", exit_code=exit_code, diagnostics=diagnostics, summary=summary
    )
