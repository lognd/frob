"""frob.webapp._websec_csrf_session coverage (T-5351): WEBSEC201-208
CSRF and session lifecycle findings, one positive + one negative fixture
per rule id under tests/fixtures/webapp/websec2xx/csrf_session/.

frob:ticket T-5351
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_csrf_session import (
    websec_csrf_session_findings,
    websec_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec2xx"
    / "csrf_session"
)

_CASES = [
    ("webesc201_positive", "WEBSEC201", True),
    ("webesc201_negative", "WEBSEC201", False),
    ("webesc202_positive", "WEBSEC202", True),
    ("webesc202_negative", "WEBSEC202", False),
    ("webesc203_positive", "WEBSEC203", True),
    ("webesc203_negative", "WEBSEC203", False),
    ("webesc204_positive", "WEBSEC204", True),
    ("webesc204_negative", "WEBSEC204", False),
    ("webesc205_positive", "WEBSEC205", True),
    ("webesc205_negative", "WEBSEC205", False),
    ("webesc206_positive", "WEBSEC206", True),
    ("webesc206_negative", "WEBSEC206", False),
    ("webesc207_positive", "WEBSEC207", True),
    ("webesc207_negative", "WEBSEC207", False),
    ("webesc208_positive", "WEBSEC208", True),
    ("webesc208_negative", "WEBSEC208", False),
]


# frob:tests src/frob/webapp/_websec_csrf_session.py::WebsecCsrfSessionFinding \
# kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_csrf_session.py::websec_csrf_session_findings \
# kind="unit"
def test_websec_csrf_session_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture fires nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_csrf_session_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_csrf_session.py::websec_csrf_session_findings \
# kind="unit"
def test_websec_csrf_session_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain an app.py
    that would otherwise plant a WEBSEC201 finding."""
    (tmp_path / "app.py").write_text(
        "@app.route('/x')\ndef x():\n    item.delete()\n", encoding="utf-8"
    )
    assert websec_csrf_session_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_csrf_session.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5308's discovery-hook
    convention) turns a WEBSEC201 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc201_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "WEBSEC201"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_csrf_session.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC201 finding."""
    root = _FIXTURE_ROOT / "webesc201_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_csrf_session_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC201
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc201_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC201"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "app.py"
