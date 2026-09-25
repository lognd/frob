"""frob.webapp._comply_privacy coverage (T-5372): COMPLY101-108
privacy-policy content lint, one positive + one negative fixture per
rule id under tests/fixtures/webapp/comply1xx/privacy/.

frob:ticket T-5372
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._comply_privacy import comply_privacy_findings, websec_findings
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "comply1xx"
    / "privacy"
)

_CASES = [
    ("missing_page", "COMPLY101", True),
    ("compliant", "COMPLY101", False),
    ("missing_categories", "COMPLY102", True),
    ("compliant", "COMPLY102", False),
    ("missing_effective_date", "COMPLY103", True),
    ("compliant", "COMPLY103", False),
    ("missing_do_not_track", "COMPLY104", True),
    ("compliant", "COMPLY104", False),
    ("missing_last_updated", "COMPLY105", True),
    ("compliant", "COMPLY105", False),
    ("stale_last_updated", "COMPLY106", True),
    ("compliant", "COMPLY106", False),
    ("missing_do_not_sell", "COMPLY107", True),
    ("compliant", "COMPLY107", False),
    ("missing_categories_sold", "COMPLY108", True),
    ("compliant", "COMPLY108", False),
]


# frob:tests \
# tests/unit/test_webapp_comply_privacy.py::test_comply_privacy_findings_fixture[missing_page-COMPLY101-True] kind="unit"  # noqa: E501
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_comply_privacy.py::comply_privacy_findings kind="unit"
def test_comply_privacy_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule id's positive fixture plants exactly that
    rule id; the shared `compliant` fixture (full content, both signals
    satisfied, a recent last_updated) is the negative control for every
    rule id at once."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = comply_privacy_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_comply_privacy.py::comply_privacy_findings kind="unit"
def test_comply_privacy_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a
    privacy.md that would otherwise plant a COMPLY102 finding."""
    (tmp_path / "privacy.md").write_text("# Privacy Policy\n", encoding="utf-8")
    assert comply_privacy_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_comply_privacy.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5308's discovery-hook
    convention, reused by this COMPLY leaf) turns a COMPLY101 finding
    into a `Violation` when handed a non-empty `frameworks` set, without
    re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "missing_page"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "COMPLY101"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_comply_privacy.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a COMPLY101 finding."""
    root = _FIXTURE_ROOT / "missing_page"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_comply_privacy_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery, widened by T-5372 to also match
    `frob.webapp._comply_*` modules) finds and calls THIS module's hook
    without any further `_taint_gate.py` edit, and reports the planted
    COMPLY101 finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "missing_page"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "COMPLY101"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
