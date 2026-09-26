"""frob.webapp._comply_commerce coverage (T-5363): COMPLY123-127
subscription/cancellation/commerce dark-pattern lint, one positive
fixture per rule id plus shared negative controls under
tests/fixtures/webapp/comply1xx/commerce/.

frob:ticket T-5363
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._comply_commerce import comply_commerce_findings, websec_findings
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "comply1xx"
    / "commerce"
)

_CASES = [
    ("no_cancel_route", "COMPLY123", True),
    ("compliant_routes", "COMPLY123", False),
    ("compliant_commerce", "COMPLY123", False),
    ("deep_cancel_route", "COMPLY124", True),
    ("compliant_routes", "COMPLY124", False),
    ("compliant_commerce", "COMPLY124", False),
    ("missing_unsubscribe", "COMPLY125", True),
    ("compliant_commerce", "COMPLY125", False),
    ("missing_postal_address", "COMPLY126", True),
    ("compliant_commerce", "COMPLY126", False),
    ("raw_card_field", "COMPLY127", True),
    ("compliant_commerce", "COMPLY127", False),
]


# frob:tests \
# tests/unit/test_webapp_comply_commerce.py::test_comply_commerce_findings_fixture[no_cancel_route-COMPLY123-True] kind="unit"  # noqa: E501
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_comply_commerce.py::comply_commerce_findings kind="unit"
def test_comply_commerce_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule id's positive fixture plants exactly that
    rule id; `compliant_routes`/`compliant_commerce` are the negative
    controls."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = comply_commerce_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_comply_commerce.py::comply_commerce_findings kind="unit"
def test_comply_commerce_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain an
    app.py with a bare subscribe route that would otherwise plant a
    COMPLY123 finding."""
    (tmp_path / "app.py").write_text('"/subscribe"\n', encoding="utf-8")
    assert comply_commerce_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_comply_commerce.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5308's discovery-hook
    convention, reused by this COMPLY leaf) turns a COMPLY123 finding
    into a `Violation` when handed a non-empty `frameworks` set, without
    re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "no_cancel_route"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "COMPLY123"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_comply_commerce.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a COMPLY123 finding."""
    root = _FIXTURE_ROOT / "no_cancel_route"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_comply_commerce_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery, already widened to `_comply_*`
    by T-5372) finds and calls THIS sibling module's hook without any
    further `_taint_gate.py` edit, and reports the planted COMPLY123
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "no_cancel_route"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "COMPLY123"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
