"""frob.webapp._websec_rls_llm coverage (T-5359): WEBSEC408-419
Supabase RLS, webhooks, payments, and LLM surface findings, one positive
+ one negative fixture per rule id under
tests/fixtures/webapp/websec4xx/rls_llm/.

frob:ticket T-5359
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_rls_llm import websec_findings, websec_rls_llm_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec4xx"
    / "rls_llm"
)

_CASES = [
    ("webesc408_positive", "WEBSEC408", True),
    ("webesc408_negative", "WEBSEC408", False),
    ("webesc409_positive", "WEBSEC409", True),
    ("webesc409_negative", "WEBSEC409", False),
    ("webesc410_positive", "WEBSEC410", True),
    ("webesc410_negative", "WEBSEC410", False),
    ("webesc411_positive", "WEBSEC411", True),
    ("webesc411_negative", "WEBSEC411", False),
    ("webesc412_positive", "WEBSEC412", True),
    ("webesc412_negative", "WEBSEC412", False),
    ("webesc413_positive", "WEBSEC413", True),
    ("webesc413_negative", "WEBSEC413", False),
    ("webesc414_positive", "WEBSEC414", True),
    ("webesc414_negative", "WEBSEC414", False),
    ("webesc415_positive", "WEBSEC415", True),
    ("webesc415_negative", "WEBSEC415", False),
    ("webesc416_positive", "WEBSEC416", True),
    ("webesc416_negative", "WEBSEC416", False),
    ("webesc417_positive", "WEBSEC417", True),
    ("webesc417_negative", "WEBSEC417", False),
    ("webesc418_positive", "WEBSEC418", True),
    ("webesc418_negative", "WEBSEC418", False),
    ("webesc419_positive", "WEBSEC419", True),
    ("webesc419_negative", "WEBSEC419", False),
]


# frob:tests src/frob/webapp/_websec_rls_llm.py::WebsecRlsLlmFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_rls_llm.py::websec_rls_llm_findings kind="unit"
def test_websec_rls_llm_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture fires nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_rls_llm_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_rls_llm.py::websec_rls_llm_findings kind="unit"
def test_websec_rls_llm_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a
    migration that would otherwise plant a WEBSEC408 finding."""
    (tmp_path / "001.sql").write_text(
        "CREATE TABLE profiles (id uuid);\n", encoding="utf-8"
    )
    assert websec_rls_llm_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_rls_llm.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5308's discovery-hook
    convention) turns a WEBSEC408 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc408_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "WEBSEC408"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_rls_llm.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC408 finding."""
    root = _FIXTURE_ROOT / "webesc408_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_rls_llm_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC408
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc408_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC408"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "001_create_profiles.sql"
