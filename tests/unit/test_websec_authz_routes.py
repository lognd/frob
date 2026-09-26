"""frob.webapp._websec_authz_routes coverage (T-5357): WEBSEC401-407
route-level authorization findings, one positive + one negative fixture
per rule id under tests/fixtures/webapp/websec4xx/routes/.

frob:ticket T-5357
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_authz_routes import (
    websec_authz_route_findings,
    websec_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec4xx" / "routes"
)

_CASES = [
    ("webesc401_positive", "WEBSEC401", True),
    ("webesc401_negative", "WEBSEC401", False),
    ("webesc402_positive", "WEBSEC402", True),
    ("webesc402_negative", "WEBSEC402", False),
    ("webesc403_positive", "WEBSEC403", True),
    ("webesc403_negative", "WEBSEC403", False),
    ("webesc404_positive", "WEBSEC404", True),
    ("webesc404_negative", "WEBSEC404", False),
    ("webesc405_positive", "WEBSEC405", True),
    ("webesc405_negative", "WEBSEC405", False),
    ("webesc406_positive", "WEBSEC406", True),
    ("webesc406_negative", "WEBSEC406", False),
    ("webesc407_positive", "WEBSEC407", True),
    ("webesc407_negative", "WEBSEC407", False),
]


# frob:tests src/frob/webapp/_websec_authz_routes.py::WebsecAuthzRouteFinding \
# kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_authz_routes.py::websec_authz_route_findings \
# kind="unit"
def test_websec_authz_route_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture (the gap closed) fires nothing for
    that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_authz_route_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_authz_routes.py::websec_authz_route_findings \
# kind="unit"
def test_websec_authz_route_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain an
    admin-path route decorator that would otherwise plant a WEBSEC402
    finding."""
    (tmp_path / "app.py").write_text(
        '@app.route("/admin/users")\ndef admin_users():\n    pass\n',
        encoding="utf-8",
    )
    assert websec_authz_route_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_authz_routes.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5311's discovery-hook
    convention) turns a WEBSEC402 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc402_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "WEBSEC402"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_authz_routes.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC402 finding."""
    root = _FIXTURE_ROOT / "webesc402_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_authz_routes_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC402
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc402_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC402"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "app.py"
