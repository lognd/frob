"""frob.webapp._websec_password coverage (T-5353): WEBSEC218-224
password policy and storage findings, one positive + one negative
fixture per rule id under tests/fixtures/webapp/websec2xx/password/.

frob:ticket T-5353
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_password import websec_findings, websec_password_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec2xx"
    / "password"
)

_CASES = [
    ("webesc218_positive", "WEBSEC218", True),
    ("webesc218_negative", "WEBSEC218", False),
    ("webesc219_positive", "WEBSEC219", True),
    ("webesc219_negative", "WEBSEC219", False),
    ("webesc220_positive", "WEBSEC220", True),
    ("webesc220_negative", "WEBSEC220", False),
    ("webesc221_positive", "WEBSEC221", True),
    ("webesc221_negative", "WEBSEC221", False),
    ("webesc222_positive", "WEBSEC222", True),
    ("webesc222_negative", "WEBSEC222", False),
    ("webesc223_positive", "WEBSEC223", True),
    ("webesc223_negative", "WEBSEC223", False),
    ("webesc224_positive", "WEBSEC224", True),
    ("webesc224_negative", "WEBSEC224", False),
]


# frob:tests src/frob/webapp/_websec_password.py::WebsecPasswordFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_password.py::websec_password_findings kind="unit"
def test_websec_password_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture (the gap closed) fires nothing for
    that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_password_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_password.py::websec_password_findings kind="unit"
def test_websec_password_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a
    `hashlib.md5(password...)` call that would otherwise plant a
    WEBSEC220 finding."""
    (tmp_path / "auth.py").write_text(
        "import hashlib\nhashlib.md5(password.encode())\n", encoding="utf-8"
    )
    assert websec_password_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_password.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5311's discovery-hook
    convention) turns a WEBSEC220 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc220_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.DJANGO}))
    matching = [v for v in violations if v.rule == "WEBSEC220"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_password.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC220 finding."""
    root = _FIXTURE_ROOT / "webesc220_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_password_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC220
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc220_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC220"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "auth.py"
