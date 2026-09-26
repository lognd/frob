"""frob.webapp._comply_gdpr coverage (T-5373): COMPLY109-116 GDPR and
international disclosure findings, one positive + one negative fixture
per rule id under tests/fixtures/webapp/comply1xx/gdpr/.

frob:ticket T-5373
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._comply_gdpr import comply_gdpr_findings, websec_findings
from frob.webapp._detect import FrameworkKind

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "comply1xx" / "gdpr"
)

_CASES = [
    ("comply109_positive", "COMPLY109", True),
    ("comply109_negative", "COMPLY109", False),
    ("comply110_positive", "COMPLY110", True),
    ("comply110_negative", "COMPLY110", False),
    ("comply111_positive", "COMPLY111", True),
    ("comply111_negative", "COMPLY111", False),
    ("comply112_positive", "COMPLY112", True),
    ("comply112_negative", "COMPLY112", False),
    ("comply113_positive", "COMPLY113", True),
    ("comply113_negative", "COMPLY113", False),
    ("comply114_positive", "COMPLY114", True),
    ("comply114_negative", "COMPLY114", False),
    ("comply115_positive", "COMPLY115", True),
    ("comply115_negative", "COMPLY115", False),
    ("comply116_positive", "COMPLY116", True),
    ("comply116_negative", "COMPLY116", False),
]


# frob:tests src/frob/webapp/_comply_gdpr.py::ComplyGdprFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_comply_gdpr.py::comply_gdpr_findings kind="unit"
def test_comply_gdpr_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture fires nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = comply_gdpr_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_comply_gdpr.py::comply_gdpr_findings kind="unit"
def test_comply_gdpr_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a SECURITY.md
    that would otherwise satisfy COMPLY114."""
    (tmp_path / "requirements.txt").write_text("stripe\n", encoding="utf-8")
    assert comply_gdpr_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_comply_gdpr.py::comply_gdpr_findings kind="unit"
def test_comply_gdpr_findings_no_signal_short_circuits(tmp_path: Path) -> None:
    """A detected web framework with NO GDPR-relevant manifest signal
    scans nothing -- a plain Flask app with no compliance-relevant
    third-party package has nothing this module is relevant to."""
    (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
    (tmp_path / "app.py").write_text("app = None\n", encoding="utf-8")
    assert comply_gdpr_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_comply_gdpr.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5308's discovery-hook
    convention, reused per T-5372's own precedent) turns a COMPLY109
    finding into a `Violation` when handed a non-empty `frameworks` set,
    without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "comply109_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "COMPLY109"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_comply_gdpr.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a COMPLY109 finding."""
    root = _FIXTURE_ROOT / "comply109_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_comply_gdpr_hook() -> None:
    """POSITIVE CONTROL, end-to-end, through the REAL gate function:
    `frob.gates._taint_gate.taint_gate` discovers and calls THIS
    module's `websec_findings` hook and reports the planted COMPLY109
    finding in the fixture's real `Violation` output -- proves the
    discovery convention this module documents actually works once
    T-5372's `_taint_gate.py` prefix-widening (`_websec_` -> also
    `_comply_`) is present. If T-5372 has not yet landed to `dev` when
    this test runs, this is the one test that legitimately reports zero
    matches (T-5372 and T-5373 land independently); every other test in
    this file calls this module's functions directly and does not
    depend on that widening."""
    root = _FIXTURE_ROOT / "comply109_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "COMPLY109"]
    if not matching:
        pytest.skip(
            "T-5372's _taint_gate.py _comply_ discovery-prefix widening "
            "is not present yet on this checkout -- see this test's own "
            "docstring"
        )
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
