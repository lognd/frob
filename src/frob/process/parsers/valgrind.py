"""
Valgrind memcheck output parser.

Supports both plain text and XML (--xml=yes) output.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

from frob.process.parsers.common import Diagnostic, ToolResult, summarize_severity

_ERROR_PAD = re.compile(r"^==\d+==")
_LEAK = re.compile(
    r"(definitely lost|indirectly lost|possibly lost|still reachable):\s*([\d,]+) bytes"
)
_INVALID = re.compile(
    r"(Invalid read|Invalid write|Use of uninitialised|Conditional jump)"
)


# frob:doc docs/process.md#public-api
def parse_valgrind(stdout: str, exit_code: int = 0) -> ToolResult:
    text = stdout.strip()
    if text.startswith("<?xml") or text.startswith("<valgrindoutput"):
        return _parse_xml(text, exit_code)
    return _parse_text(text, exit_code)


# frob:ticket T-0045
def _split_error_blocks(clean: list[str]) -> list[list[str]]:
    """Group cleaned valgrind lines into blank-line-separated error blocks."""
    error_blocks: list[list[str]] = []
    current: list[str] = []
    for line in clean:
        if line == "" and current:
            if any(current):
                error_blocks.append(current)
            current = []
        else:
            current.append(line)
    return error_blocks


# frob:ticket T-0045
def _invalid_diagnostic(block: list[str]) -> Diagnostic | None:
    """An error Diagnostic for an Invalid-read/write block, else None."""
    first = block[0] if block else ""
    if not (_INVALID.search(first) or "Invalid" in first):
        return None
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
    return Diagnostic(file=file_ref, line=lineno, severity="error", message=first[:120])


# frob:ticket T-0045
def _leak_diagnostic(line: str) -> Diagnostic | None:
    """A leak Diagnostic for a valgrind leak-summary line, else None."""
    m = _LEAK.search(line)
    if not m:
        return None
    kind, amount = m.groups()
    if kind in ("definitely lost", "indirectly lost"):
        return Diagnostic(
            severity="error", message=f"memory leak ({kind}): {amount} bytes"
        )
    return Diagnostic(severity="warning", message=f"memory ({kind}): {amount} bytes")


def _parse_text(text: str, exit_code: int) -> ToolResult:
    # Strip pid prefix ==1234==
    clean = [_ERROR_PAD.sub("", ln).strip() for ln in text.splitlines()]

    diagnostics: list[Diagnostic] = []
    for block in _split_error_blocks(clean):
        diag = _invalid_diagnostic(block)
        if diag is not None:
            diagnostics.append(diag)
    for line in clean:
        diag = _leak_diagnostic(line)
        if diag is not None:
            diagnostics.append(diag)

    err_summary = next((ln for ln in clean if "ERROR SUMMARY:" in ln), None)
    summary = err_summary or summarize_severity(diagnostics, empty="clean")
    return ToolResult(
        tool="valgrind",
        exit_code=exit_code,
        diagnostics=diagnostics,
        summary=summary.strip(),
    )


# frob:ticket T-0045
def _xml_error_diagnostic(error: ET.Element) -> Diagnostic:
    """A Diagnostic for one valgrind XML `<error>` element."""
    kind = (error.findtext("kind") or "").lower()
    what = error.findtext("what") or error.findtext("xwhat/text") or kind
    sev = "error" if "definite" in kind or "invalid" in kind else "warning"
    file_ref: str | None = None
    lineno: int | None = None
    for frame in error.findall(".//frame"):
        fn = frame.findtext("file")
        ln = frame.findtext("line")
        if fn and ln:
            file_ref = fn
            lineno = int(ln)
            break
    return Diagnostic(
        file=file_ref, line=lineno, severity=sev, message=(what or "")[:120]
    )


def _parse_xml(text: str, exit_code: int) -> ToolResult:
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return ToolResult(
            tool="valgrind", exit_code=exit_code, summary="XML parse error"
        )

    diagnostics = [_xml_error_diagnostic(error) for error in root.findall(".//error")]
    summary = summarize_severity(diagnostics, empty="clean")
    return ToolResult(
        tool="valgrind", exit_code=exit_code, diagnostics=diagnostics, summary=summary
    )
