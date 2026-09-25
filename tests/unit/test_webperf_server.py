"""frob.webapp._webperf_server coverage (T-5366): WEBPERF109-115
server/network performance-config findings, one positive + one negative
fixture per rule id under tests/fixtures/webapp/webperf1xx/server/.

frob:ticket T-5366
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.webapp._detect import FrameworkKind
from frob.webapp._webperf_server import webperf_server_findings, websec_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "webperf1xx"
    / "server"
)

_CASES = [
    ("webperf109_positive", "WEBPERF109", True),
    ("webperf109_negative", "WEBPERF109", False),
    ("webperf110_positive", "WEBPERF110", True),
    ("webperf110_negative", "WEBPERF110", False),
    ("webperf111_positive", "WEBPERF111", True),
    ("webperf111_negative", "WEBPERF111", False),
    ("webperf112_positive", "WEBPERF112", True),
    ("webperf112_negative", "WEBPERF112", False),
    ("webperf113_positive", "WEBPERF113", True),
    ("webperf113_negative", "WEBPERF113", False),
    ("webperf114_positive", "WEBPERF114", True),
    ("webperf114_negative", "WEBPERF114", False),
    ("webperf115_positive", "WEBPERF115", True),
    ("webperf115_negative", "WEBPERF115", False),
]


# frob:tests src/frob/webapp/_webperf_server.py::WebsecWebperfServerFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_webperf_server.py::webperf_server_findings kind="unit"
def test_webperf_server_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture (the config gap closed) fires
    nothing for that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = webperf_server_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) >= 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_webperf_server.py::webperf_server_findings kind="unit"
def test_webperf_server_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a plain
    nginx.conf with no Cache-Control that would otherwise plant a
    WEBPERF110 finding."""
    (tmp_path / "nginx.conf").write_text(
        "server { location / { proxy_pass http://app; } }\n", encoding="utf-8"
    )
    assert webperf_server_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_webperf_server.py::websec_findings kind="unit"
def test_websec_findings_emits_violation_when_called_directly() -> None:
    """`websec_findings(root, frameworks)` turns a WEBPERF110 finding
    into a `Violation` when handed a non-empty `frameworks` set, without
    re-running `detect_frameworks` -- called directly (module
    docstring's DISCOVERY section: no live gate discovers this hook
    yet)."""
    root = _FIXTURE_ROOT / "webperf110_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "WEBPERF110"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_webperf_server.py::websec_findings kind="unit"
def test_websec_findings_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBPERF110 finding."""
    root = _FIXTURE_ROOT / "webperf110_positive"
    assert websec_findings(root, frozenset()) == ()
