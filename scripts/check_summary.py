"""Summarise `frob check --json` output: severity counts and every error.

WHY THIS EXISTS. The coordinator loop measures main's error floor after
every batch of lands. `frob check --json` nests severity two levels deep
(`results[].diagnostics[].severity`, NOT a top-level `findings` list), and
reading it at the wrong level silently reports zero -- which happened, and
produced two false "0 errors" reports before it was caught. This encodes
the correct traversal once instead of re-deriving it inline each time.

Usage:
    uv run frob check --json > out.json && python3 scripts/check_summary.py out.json
    uv run frob check --json | python3 scripts/check_summary.py
"""

from __future__ import annotations

import collections
import json
import sys
from typing import Any


# frob:doc docs/guides/coordinator-scripts.md#load_report
# frob:ticket T-1863
# frob:tests tests/unit/test_coordinator_scripts.py::TestLoadReport.test_reads_path
# frob:tests tests/unit/test_coordinator_scripts.py::TestLoadReport.test_reads_stdin
def load_report(source: str | None) -> dict[str, Any]:
    """Read a `frob check --json` report from a path, or stdin when None."""
    if source is None or source == "-":
        return json.load(sys.stdin)
    with open(source, encoding="utf-8") as handle:
        return json.load(handle)


# frob:doc docs/guides/coordinator-scripts.md#iter_diagnostics
# frob:ticket T-1863
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestIterDiagnostics.test_yields_tool_and_diag\
# nostic
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestIterDiagnostics.test_empty_results
def iter_diagnostics(report: dict[str, Any]):
    """Yield (tool, diagnostic) for every diagnostic in the report.

    The nesting is `report["results"]` -> tool record -> `["diagnostics"]`.
    Severity lives on the DIAGNOSTIC, not the tool record; that distinction
    is the whole reason this helper exists.
    """
    for record in report.get("results", []):
        tool = record.get("tool")
        for diagnostic in record.get("diagnostics", []):
            yield tool, diagnostic


# frob:doc docs/guides/coordinator-scripts.md#summarise
# frob:ticket T-1863
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSummarise.test_counts_by_severity
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestSummarise.test_collects_error_rows
def summarise(report: dict[str, Any]) -> tuple[collections.Counter, list[tuple]]:
    """Return (severity counts, error rows) for a parsed report."""
    severities: collections.Counter = collections.Counter()
    errors: list[tuple] = []
    for tool, diagnostic in iter_diagnostics(report):
        severity = diagnostic.get("severity")
        severities[severity] += 1
        if severity == "error":
            errors.append(
                (
                    tool,
                    diagnostic.get("code"),
                    diagnostic.get("file"),
                    diagnostic.get("line"),
                    (diagnostic.get("message") or "")[:120],
                )
            )
    return severities, errors


# frob:doc docs/guides/coordinator-scripts.md#check_summary-main
# frob:ticket T-1863
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain.test_exit_zero_when_clean
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain.test_exit_one_when_errors
def main() -> int:
    """Print severity counts then every error row; exit 1 if any error."""
    report = load_report(sys.argv[1] if len(sys.argv) > 1 else None)
    severities, errors = summarise(report)
    print(f"SEVERITY {dict(severities)}")
    print(f"ERRORS   {len(errors)}")
    for tool, code, path, line, message in errors:
        print(f"  {tool}:{code} {path}:{line} | {message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
