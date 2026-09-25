"""frob.webapp._websec_random_tls coverage (T-5354): WEBSEC226-230
randomness and TLS verification findings, one positive + one negative
fixture per rule id under tests/fixtures/webapp/websec2xx/random_tls/.

frob:ticket T-5354
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_random_tls import (
    websec_findings,
    websec_random_tls_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec2xx"
    / "random_tls"
)

_CASES = [
    ("webesc226_positive", "WEBSEC226", True),
    ("webesc226_negative", "WEBSEC226", False),
    ("webesc227_positive", "WEBSEC227", True),
    ("webesc227_negative", "WEBSEC227", False),
    ("webesc228_positive", "WEBSEC228", True),
    ("webesc228_negative", "WEBSEC228", False),
    ("webesc229_positive", "WEBSEC229", True),
    ("webesc229_negative", "WEBSEC229", False),
    ("webesc230_positive", "WEBSEC230", True),
    ("webesc230_negative", "WEBSEC230", False),
]


# frob:tests src/frob/webapp/_websec_random_tls.py::WebsecRandomTlsFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_random_tls.py::websec_random_tls_findings \
# kind="unit"
def test_websec_random_tls_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture fires nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_random_tls_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_random_tls.py::websec_random_tls_findings \
# kind="unit"
def test_websec_random_tls_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain an app.py
    that would otherwise plant a WEBSEC226 finding."""
    (tmp_path / "app.py").write_text(
        "session_token = random.random()\n", encoding="utf-8"
    )
    assert websec_random_tls_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_random_tls.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5308's discovery-hook
    convention) turns a WEBSEC226 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc226_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "WEBSEC226"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_random_tls.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC226 finding."""
    root = _FIXTURE_ROOT / "webesc226_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_random_tls_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC226
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc226_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC226"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "app.py"
