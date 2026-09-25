"""frob.webapp._websec_tokens coverage (T-5352): WEBSEC209-216 JWT and
OAuth token findings, one positive + one negative fixture per rule id
under tests/fixtures/webapp/websec2xx/jwt_oauth/.

frob:ticket T-5352
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_tokens import websec_findings, websec_token_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec2xx"
    / "jwt_oauth"
)

_CASES = [
    ("webesc209_positive", "WEBSEC209", True),
    ("webesc209_negative", "WEBSEC209", False),
    ("webesc210_positive", "WEBSEC210", True),
    ("webesc210_negative", "WEBSEC210", False),
    ("webesc211_positive", "WEBSEC211", True),
    ("webesc211_negative", "WEBSEC211", False),
    ("webesc212_positive", "WEBSEC212", True),
    ("webesc212_negative", "WEBSEC212", False),
    ("webesc213_positive", "WEBSEC213", True),
    ("webesc213_negative", "WEBSEC213", False),
    ("webesc214_positive", "WEBSEC214", True),
    ("webesc214_negative", "WEBSEC214", False),
    ("webesc215_positive", "WEBSEC215", True),
    ("webesc215_negative", "WEBSEC215", False),
    ("webesc216_positive", "WEBSEC216", True),
    ("webesc216_negative", "WEBSEC216", False),
]


# frob:tests src/frob/webapp/_websec_tokens.py::WebsecTokenFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_tokens.py::websec_token_findings kind="unit"
def test_websec_token_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture (clean/complete call-argument or
    config shape) fires nothing for that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_token_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_tokens.py::websec_token_findings kind="unit"
def test_websec_token_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a
    `jwt.decode(...)` call that would otherwise plant a WEBSEC210
    finding."""
    (tmp_path / "auth.py").write_text(
        'import jwt\njwt.decode(token, key, algorithms=["HS256"])\n',
        encoding="utf-8",
    )
    assert websec_token_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_tokens.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5311's discovery-hook
    convention) turns a WEBSEC210 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc210_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.DJANGO}))
    matching = [v for v in violations if v.rule == "WEBSEC210"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_tokens.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC210 finding."""
    root = _FIXTURE_ROOT / "webesc210_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_tokens_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC210
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc210_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC210"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "auth.py"
