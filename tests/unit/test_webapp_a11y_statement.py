"""frob.webapp._a11y_statement coverage: positive/negative controls for
the accessibility-statement content-lint.

frob:ticket T-5324
"""

from __future__ import annotations

from pathlib import Path

from frob.webapp._a11y_statement import a11y_findings
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "a11y1xx"
    / "statement"
)


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
def test_a11y_findings_complete_statement_is_clean():
    """MUST-STAY-QUIET: a statement page covering all seven required
    sections reports no findings at all."""
    findings = a11y_findings(
        _FIXTURE_ROOT / "complete", frozenset({FrameworkKind.NEXTJS})
    )
    assert findings == ()


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
# frob:tests src/frob/webapp/_a11y_statement.py::_StatementSection kind="unit"
def test_a11y_findings_partial_statement_reports_missing_sections():
    """MUST-FIRE: a statement page covering only commitment+contact reports
    the five other required sections as missing, each its own rule id, and
    none of the two present sections."""
    findings = a11y_findings(
        _FIXTURE_ROOT / "partial", frozenset({FrameworkKind.NEXTJS})
    )
    rules = {v.rule for v in findings}
    assert rules == {"A11Y108", "A11Y110", "A11Y111", "A11Y112", "A11Y113"}
    assert all(v.file == "pages/accessibility.tsx" for v in findings)


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
def test_a11y_findings_missing_page_reports_single_precondition_finding():
    """MUST-FIRE: a repo with no accessibility statement page/route at all
    reports exactly one A11Y114 finding, not one per section."""
    findings = a11y_findings(
        _FIXTURE_ROOT / "missing", frozenset({FrameworkKind.NEXTJS})
    )
    assert len(findings) == 1
    assert findings[0].rule == "A11Y114"


# frob:tests src/frob/webapp/_a11y_statement.py::a11y_findings kind="unit"
def test_a11y_findings_no_frameworks_reports_missing_page():
    """An empty `frameworks` set can never locate any page, so it reports
    the same single A11Y114 finding as a repo with no matching route."""
    findings = a11y_findings(_FIXTURE_ROOT / "complete", frozenset())
    assert len(findings) == 1
    assert findings[0].rule == "A11Y114"
