"""frob.webapp._websec_xss coverage (T-5306): WEBSEC107-108 Rails ERB
explicit-unescaped-tag and PHP raw-superglobal-echo findings, one
positive + one negative fixture per rule id under
tests/fixtures/webapp/websec1xx/xss/.

frob:ticket T-5306
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_xss import websec_findings, websec_xss_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec1xx" / "xss"
)

_CASES = [
    ("webesc107_positive", "WEBSEC107", True),
    ("webesc107_negative", "WEBSEC107", False),
    ("webesc108_positive", "WEBSEC108", True),
    ("webesc108_negative", "WEBSEC108", False),
]


# frob:tests src/frob/webapp/_websec_xss.py::WebsecXssFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_xss.py::websec_xss_findings kind="unit"
def test_websec_xss_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each sink's positive fixture plants exactly that rule id;
    the matching negative fixture (literal/sanitized value) fires nothing."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_xss_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_xss.py::websec_xss_findings kind="unit"
def test_websec_xss_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a `.php`
    file that would otherwise plant a WEBSEC108 finding."""
    (tmp_path / "index.php").write_text(
        "<?php\necho $_GET['name'];\n", encoding="utf-8"
    )
    assert websec_xss_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_xss.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5311's discovery-hook
    convention) turns a WEBSEC108 finding into a `Violation` when handed a
    non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc108_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.LARAVEL}))
    matching = [v for v in violations if v.rule == "WEBSEC108"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_xss.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set without
    touching the filesystem, even over a fixture that would otherwise
    plant a WEBSEC108 finding."""
    root = _FIXTURE_ROOT / "webesc108_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_xss_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC108
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc108_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC108"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "index.php"
