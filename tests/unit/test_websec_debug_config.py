"""frob.webapp._websec_debug_config coverage (T-5329): WEBSEC310-316
debug/info-leak configuration findings, one positive + one negative
fixture per rule id under tests/fixtures/webapp/websec3xx/debug/.

frob:ticket T-5329
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_debug_config import (
    websec_debug_config_findings,
    websec_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec3xx" / "debug"
)

_CASES = [
    ("webesc310_positive", "WEBSEC310", True),
    ("webesc310_negative", "WEBSEC310", False),
    ("webesc311_positive", "WEBSEC311", True),
    ("webesc311_negative", "WEBSEC311", False),
    ("webesc312_positive", "WEBSEC312", True),
    ("webesc312_negative", "WEBSEC312", False),
    ("webesc313_positive", "WEBSEC313", True),
    ("webesc313_negative", "WEBSEC313", False),
    ("webesc314_positive", "WEBSEC314", True),
    ("webesc314_negative", "WEBSEC314", False),
    ("webesc315_positive", "WEBSEC315", True),
    ("webesc315_negative", "WEBSEC315", False),
    ("webesc316_positive", "WEBSEC316", True),
    ("webesc316_negative", "WEBSEC316", False),
]


# frob:tests src/frob/webapp/_websec_debug_config.py::WebsecDebugConfigFinding \
# kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_debug_config.py::websec_debug_config_findings \
# kind="unit"
def test_websec_debug_config_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture (clean/sanitized configuration)
    fires nothing for that rule id."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_debug_config_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_debug_config.py::websec_debug_config_findings \
# kind="unit"
def test_websec_debug_config_findings_map_file_variant() -> None:
    """WEBSEC311's second detection path -- a tracked `.js.map` file
    under a build-output (`static/`) directory -- fires independently of
    the webpack `devtool` config check; a plain `.js` file with no
    tracked map sibling fires nothing."""
    positive = websec_debug_config_findings(_FIXTURE_ROOT / "webesc311_map_positive")
    assert any(f.rule == "WEBSEC311" for f in positive), positive
    negative = websec_debug_config_findings(_FIXTURE_ROOT / "webesc311_map_negative")
    assert not any(f.rule == "WEBSEC311" for f in negative), negative


# frob:tests src/frob/webapp/_websec_debug_config.py::websec_debug_config_findings \
# kind="unit"
def test_websec_debug_config_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a
    `settings.py` with `DEBUG = True` that would otherwise plant a
    WEBSEC310 finding."""
    (tmp_path / "settings.py").write_text("DEBUG = True\n", encoding="utf-8")
    assert websec_debug_config_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_debug_config.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5311's discovery-hook
    convention) turns a WEBSEC310 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc310_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.DJANGO}))
    matching = [v for v in violations if v.rule == "WEBSEC310"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_debug_config.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC310 finding."""
    root = _FIXTURE_ROOT / "webesc310_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_debug_config_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC310
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc310_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC310"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "settings.py"
