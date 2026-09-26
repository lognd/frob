"""frob.webapp._websec_logging_limits coverage (T-5332): WEBSEC326-334
auth-event/log-hygiene and outbound/server/body resource-limit
findings, one positive + one negative fixture per rule id under
tests/fixtures/webapp/websec3xx/logging/.

Gate wiring is the `websec_findings(root, frameworks) -> tuple[Violation,
...]` module-level hook `frob.gates._taint_gate.taint_gate` auto-
discovers from every `frob.webapp._websec_*` module (T-5308's discovery
mechanism) -- `test_websec_findings_hook_*` below cover the hook
directly, and `test_taint_gate_emits_websec326_violation` covers the
discovery mechanism end to end with a real git repo.

frob:ticket T-5332
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import detect_frameworks
from frob.webapp._websec_logging_limits import (
    websec_findings,
    websec_logging_limits_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec3xx"
    / "logging"
)

_CASES = [
    ("websec326_positive", "WEBSEC326", True),
    ("websec326_negative", "WEBSEC326", False),
    ("websec327_positive", "WEBSEC327", True),
    ("websec327_negative", "WEBSEC327", False),
    ("websec328_positive", "WEBSEC328", True),
    ("websec328_negative", "WEBSEC328", False),
    ("websec329_positive", "WEBSEC329", True),
    ("websec329_negative", "WEBSEC329", False),
    ("websec330_positive", "WEBSEC330", True),
    ("websec330_negative", "WEBSEC330", False),
    ("websec331_positive", "WEBSEC331", True),
    ("websec331_negative", "WEBSEC331", False),
    ("websec332_positive", "WEBSEC332", True),
    ("websec332_negative", "WEBSEC332", False),
    ("websec333_positive", "WEBSEC333", True),
    ("websec333_negative", "WEBSEC333", False),
    ("websec334_positive", "WEBSEC334", True),
    ("websec334_negative", "WEBSEC334", False),
]


# frob:tests src/frob/webapp/_websec_logging_limits.py::WebsecLoggingLimitsFinding \
# kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_logging_limits.py::websec_logging_limits_findings \
# kind="unit"
def test_websec_logging_limits_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants at least that rule
    id; the matching negative fixture (guarded/encoded/configured value)
    fires nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_logging_limits_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) >= 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_logging_limits.py::websec_logging_limits_findings \
# kind="unit"
def test_websec_logging_limits_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a `.py`
    file that would otherwise plant a WEBSEC326 finding."""
    (tmp_path / "auth_views.py").write_text(
        "def login(request):\n    return authenticate(request)\n",
        encoding="utf-8",
    )
    assert websec_logging_limits_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_logging_limits.py::websec_findings kind="unit"
def test_websec_findings_hook_emits_gate_violation() -> None:
    """MUST-FIRE (positive control): the `taint_gate` module-discovery
    hook, called the way `taint_gate` calls it (with the caller's own
    already-computed `detect_frameworks` result), turns the WEBSEC326
    fixture into one WARN-tier `Violation`."""
    root = _FIXTURE_ROOT / "websec326_positive"
    frameworks = detect_frameworks(root)
    assert frameworks
    violations = websec_findings(root, frameworks)
    matching = [v for v in violations if v.rule == "WEBSEC326"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "auth_views.py"


# frob:tests src/frob/webapp/_websec_logging_limits.py::websec_findings kind="unit"
def test_websec_findings_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` never re-detects frameworks itself -- an empty
    `frameworks` set (the caller's own `detect_frameworks` result) short-
    circuits to `()` even for a fixture directory that would otherwise
    plant a finding."""
    root = _FIXTURE_ROOT / "websec326_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_logging_limits_hook(tmp_path: Path) -> None:
    """MUST-FIRE (positive control): a real git repo with a Django
    framework marker plus one auth-event handler with no logger call
    produces a `WEBSEC326` `Violation` through `taint_gate` end to end --
    discovery finds `_websec_logging_limits.websec_findings` with no
    hard-coded `_taint_gate.py` call site for this rule family."""
    import subprocess as sp

    sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True)
    sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
    (tmp_path / "manage.py").write_text("import django\n", encoding="utf-8")
    (tmp_path / "auth_views.py").write_text(
        "def login(request):\n    user = authenticate(request)\n    return user\n",
        encoding="utf-8",
    )
    sp.run(["git", "add", "."], cwd=tmp_path, check=True)
    sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

    violations = taint_gate(tmp_path)
    websec = [v for v in violations if v.rule == "WEBSEC326"]
    assert len(websec) == 1
    assert websec[0].severity.value == "warn"
    assert websec[0].file == "auth_views.py"
