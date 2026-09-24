"""frob.webapp._websec_headers_rules coverage (T-5326): WEBSEC301-309
config/headers rule-id wiring over `frob.webapp._websec_headers.
lint_response_headers`, one positive + one negative fixture per rule id
under tests/fixtures/webapp/websec3xx/headers/.

frob:ticket T-5326
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_headers_rules import (
    websec_findings,
    websec_headers_rules_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec3xx"
    / "headers"
)

_CASES = [
    ("websec301_positive", "WEBSEC301", True),
    ("websec301_negative", "WEBSEC301", False),
    ("websec302_positive", "WEBSEC302", True),
    ("websec302_negative", "WEBSEC302", False),
    ("websec303_positive", "WEBSEC303", True),
    ("websec303_negative", "WEBSEC303", False),
    ("websec304_positive", "WEBSEC304", True),
    ("websec304_negative", "WEBSEC304", False),
    ("websec305_positive", "WEBSEC305", True),
    ("websec305_negative", "WEBSEC305", False),
    ("websec306_positive", "WEBSEC306", True),
    ("websec306_negative", "WEBSEC306", False),
    ("websec307_positive", "WEBSEC307", True),
    ("websec307_negative", "WEBSEC307", False),
    ("websec308_positive", "WEBSEC308", True),
    ("websec308_negative", "WEBSEC308", False),
    ("websec309_positive", "WEBSEC309", True),
    ("websec309_negative", "WEBSEC309", False),
]


# frob:tests \
# tests/unit/test_websec_headers_rules.py::test_websec_headers_rules_findings_fixture[websec301_positive-WEBSEC301-True] kind="unit"  # noqa: E501
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_headers_rules.py::websec_headers_rules_findings \
# kind="unit"
def test_websec_headers_rules_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule id's positive fixture plants exactly that rule
    id; the matching negative fixture (correct value/no wildcard/no gap)
    fires nothing for that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_headers_rules_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_headers_rules.py::websec_headers_rules_findings \
# kind="unit"
def test_websec_headers_rules_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain an
    nginx.conf that would otherwise plant a WEBSEC301 finding."""
    (tmp_path / "nginx.conf").write_text(
        'server {\n    add_header Strict-Transport-Security "max-age=1" always;\n}\n',
        encoding="utf-8",
    )
    assert websec_headers_rules_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_headers_rules.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5311's discovery-hook
    convention) turns a WEBSEC301 finding into a `Violation` when handed a
    non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "websec301_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "WEBSEC301"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_headers_rules.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set without
    touching the filesystem, even over a fixture that would otherwise
    plant a WEBSEC301 finding."""
    root = _FIXTURE_ROOT / "websec301_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_headers_rules_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC301
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "websec301_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC301"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
