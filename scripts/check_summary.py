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


# frob:doc docs/guides/coordinator-scripts.md#find_test006
# frob:ticket T-2763
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFindTest006.test_finds_test006_diagnostics
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestFindTest006.test_empty_when_no_test006
def find_test006(report: dict[str, Any]) -> list[tuple]:
    """Return every TEST006 (missing/stale coverage stamp) diagnostic.

    WHY THIS EXISTS (T-2763): TEST006 fires at ERROR when the coverage
    stamp TEST005 depends on is missing or stale, but a single TEST006
    line inside dozens of unrelated findings is easy to lose -- an agent
    scanning for "TEST005" findings sees zero and reads that as a clean
    measurement, missing the TEST006 line that says the measurement never
    happened at all. Surfacing it separately, ahead of the general
    summary, makes that distinction impossible to miss.
    """
    return [
        (tool, diagnostic.get("message") or "")
        for tool, diagnostic in iter_diagnostics(report)
        if diagnostic.get("code") == "TEST006"
    ]


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
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain.test_test006_banner_lead\
# s_output_when_present
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestCheckSummaryMain.test_no_banner_when_test\
# 006_absent
def main() -> int:
    """Print severity counts then every error row; exit 1 if any error."""
    report = load_report(sys.argv[1] if len(sys.argv) > 1 else None)
    test006 = find_test006(report)
    if test006:
        print(
            "COVERAGE STALE/MISSING (TEST006): TEST005 findings below are"
            " NOT a clean measurement -- coverage data could not be read"
        )
        for tool, message in test006:
            print(f"  {tool}:TEST006 | {message}")
    severities, errors = summarise(report)
    print(f"SEVERITY {dict(severities)}")
    # frob:waive RENDER001 reason="pre-existing bare-print CLI output (T-1863), unmoved"
    print(f"ERRORS   {len(errors)}")
    for tool, code, path, line, message in errors:
        # frob:waive RENDER001 reason="pre-existing bare print (T-1863), unmoved"
        print(f"  {tool}:{code} {path}:{line} | {message}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
