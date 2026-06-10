"""
PyCharm headless inspection output parser.

Parses the XML files produced by PyCharm's inspect.bat into Diagnostic objects.
Each XML file corresponds to one inspection category (e.g. PyUnresolvedReferences).
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from frob.logging import get_logger
from frob.process.parsers.common import Diagnostic, Severity, ToolResult

_log = get_logger(__name__)

_SEVERITY_MAP: dict[str, Severity] = {
    "ERROR": "error",
    "WARNING": "warning",
    "WEAK WARNING": "warning",
    "INFORMATION": "info",
    "SERVER PROBLEM": "warning",
}


def _map_severity(raw: str) -> Severity:
    return _SEVERITY_MAP.get(raw.strip().upper(), "warning")


def _normalize_path(raw: str, project_root: Path | None = None) -> str:
    # Strip file:/// prefix
    path = raw
    if path.startswith("file:///"):
        path = path[8:]
    elif path.startswith("file://"):
        path = path[7:]

    # Normalize backslashes to forward slashes
    path = path.replace("\\", "/")

    if project_root is not None:
        try:
            # Build a Path from the (possibly Windows-style) string
            p = Path(path)
            root = Path(str(project_root).replace("\\", "/"))
            rel = p.relative_to(root)
            return str(rel).replace("\\", "/")
        except ValueError:
            pass

    return path


def parse_pycharm_xml(xml_content: str, *, source_file: str = "") -> list[Diagnostic]:
    """Parse a single PyCharm inspection XML file into Diagnostic objects."""
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError as exc:
        _log.warning("pycharm: malformed XML in %s: %s", source_file or "<input>", exc)
        return []

    diagnostics: list[Diagnostic] = []
    for problem in root.findall("problem"):
        file_el = problem.find("file")
        line_el = problem.find("line")
        desc_el = problem.find("description")
        pc_el = problem.find("problem_class")

        raw_file = (file_el.text or "").strip() if file_el is not None else ""
        raw_line = (line_el.text or "").strip() if line_el is not None else ""
        message = (desc_el.text or "").strip() if desc_el is not None else ""
        # CDATA sections are decoded automatically by ElementTree
        # Strip any leftover markup artifacts
        message = message.strip()

        code: str | None = None
        severity: Severity = "warning"
        if pc_el is not None:
            code = pc_el.get("id") or None
            raw_sev = pc_el.get("severity", "WARNING")
            severity = _map_severity(raw_sev)

        line_num: int | None = None
        if raw_line:
            try:
                line_num = int(raw_line)
            except ValueError:
                pass

        diagnostics.append(Diagnostic(
            file=raw_file if raw_file else None,
            line=line_num,
            severity=severity,
            code=code,
            message=message,
        ))

    return diagnostics


def parse_pycharm_dir(
    output_dir: Path,
    *,
    project_root: Path | None = None,
) -> ToolResult:
    """
    Parse all XML files in a PyCharm inspection output directory.
    Aggregates all problems from all inspection categories.
    project_root: if given, make file paths relative to it.
    """
    all_diagnostics: list[Diagnostic] = []

    xml_files = sorted(output_dir.glob("*.xml"))
    if not xml_files:
        _log.warning("pycharm: no XML files found in %s", output_dir)

    for xml_file in xml_files:
        try:
            content = xml_file.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            _log.warning("pycharm: cannot read %s: %s", xml_file, exc)
            continue

        diags = parse_pycharm_xml(content, source_file=str(xml_file))
        for d in diags:
            if d.file:
                normalized = _normalize_path(d.file, project_root)
                d = d.model_copy(update={"file": normalized})
            all_diagnostics.append(d)

    errors = sum(1 for d in all_diagnostics if d.severity == "error")
    warnings = sum(1 for d in all_diagnostics if d.severity == "warning")
    files = {d.file for d in all_diagnostics if d.file}

    if all_diagnostics:
        summary = f"{errors} errors, {warnings} warnings across {len(files)} files"
    else:
        summary = "ok"

    return ToolResult(
        tool="pycharm",
        exit_code=1 if errors else 0,
        diagnostics=all_diagnostics,
        summary=summary,
    )
