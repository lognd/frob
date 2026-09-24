"""frob.webapp._launch_checklist coverage (T-5361): LAUNCH101-107
advisory-only pre-launch checklist findings, one positive + one
negative fixture per rule id under tests/fixtures/webapp/launch1xx/.

frob:ticket T-5361
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.findings import Severity
from frob.webapp._detect import FrameworkKind
from frob.webapp._launch_checklist import launch_checklist_findings, websec_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "launch1xx"
)

_CASES = [
    ("launch101_positive", "LAUNCH101", True),
    ("launch101_negative", "LAUNCH101", False),
    ("launch102_positive", "LAUNCH102", True),
    ("launch102_negative", "LAUNCH102", False),
    ("launch103_positive", "LAUNCH103", True),
    ("launch103_negative", "LAUNCH103", False),
    ("launch104_positive", "LAUNCH104", True),
    ("launch104_negative", "LAUNCH104", False),
    ("launch105_positive", "LAUNCH105", True),
    ("launch105_negative", "LAUNCH105", False),
    ("launch106_positive", "LAUNCH106", True),
    ("launch106_negative", "LAUNCH106", False),
    ("launch107_positive", "LAUNCH107", True),
    ("launch107_negative", "LAUNCH107", False),
]


# frob:tests src/frob/webapp/_launch_checklist.py::WebsecLaunchChecklistFinding \
# kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_launch_checklist.py::launch_checklist_findings kind="unit"
def test_launch_checklist_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture (the checklist item
    missing repo-wide) plants exactly that rule id; the matching
    negative fixture (the item present) fires nothing for that rule
    id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = launch_checklist_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) >= 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_launch_checklist.py::launch_checklist_findings kind="unit"
def test_launch_checklist_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even with no team/case-study/thank-you
    page anywhere (which would otherwise plant several findings)."""
    assert launch_checklist_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_launch_checklist.py::websec_findings kind="unit"
def test_websec_findings_emits_advisory_severity_never_warn_or_error() -> None:
    """OWNER DIRECTIVE (ticket body): every LAUNCH finding is
    Severity.ADVISORY, never WARN, never ERROR -- called directly
    (module docstring's DISCOVERY section: no live gate discovers this
    hook yet)."""
    root = _FIXTURE_ROOT / "launch101_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "LAUNCH101"]
    assert len(matching) == 1, violations
    assert matching[0].severity == Severity.ADVISORY
    assert matching[0].severity != Severity.WARN
    assert matching[0].severity != Severity.ERROR


# frob:tests src/frob/webapp/_launch_checklist.py::websec_findings kind="unit"
def test_websec_findings_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a LAUNCH101 finding."""
    root = _FIXTURE_ROOT / "launch101_positive"
    assert websec_findings(root, frozenset()) == ()
