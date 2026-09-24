"""frob.webapp._websec_supply_chain coverage (T-5331): WEBSEC318-325
CI/supply-chain hardening findings, one positive + one negative fixture
per rule id under tests/fixtures/webapp/websec3xx/supply/.

frob:ticket T-5331
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind
from frob.webapp._websec_supply_chain import (
    websec_findings,
    websec_supply_chain_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec3xx" / "supply"
)

_CASES = [
    ("webesc318_positive", "WEBSEC318", True),
    ("webesc318_negative", "WEBSEC318", False),
    ("webesc319_positive", "WEBSEC319", True),
    ("webesc319_negative", "WEBSEC319", False),
    ("webesc320_positive", "WEBSEC320", True),
    ("webesc320_negative", "WEBSEC320", False),
    ("webesc321_positive", "WEBSEC321", True),
    ("webesc321_negative", "WEBSEC321", False),
    ("webesc322_positive", "WEBSEC322", True),
    ("webesc322_negative", "WEBSEC322", False),
    ("webesc323_positive", "WEBSEC323", True),
    ("webesc323_negative", "WEBSEC323", False),
    ("webesc324_positive", "WEBSEC324", True),
    ("webesc324_negative", "WEBSEC324", False),
    ("webesc325_positive", "WEBSEC325", True),
    ("webesc325_negative", "WEBSEC325", False),
]


# frob:tests src/frob/webapp/_websec_supply_chain.py::WebsecSupplyChainFinding \
# kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_supply_chain.py::websec_supply_chain_findings \
# kind="unit"
def test_websec_supply_chain_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule
    id; the matching negative fixture fires nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_supply_chain_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_supply_chain.py::websec_supply_chain_findings \
# kind="unit"
def test_websec_supply_chain_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a
    Dockerfile that would otherwise plant a WEBSEC321 finding."""
    (tmp_path / "Dockerfile").write_text("FROM python:latest\n", encoding="utf-8")
    assert websec_supply_chain_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_supply_chain.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_emits_violation() -> None:
    """`websec_findings(root, frameworks)` (T-5308's discovery-hook
    convention) turns a WEBSEC321 finding into a `Violation` when handed
    a non-empty `frameworks` set, without re-running `detect_frameworks`."""
    root = _FIXTURE_ROOT / "webesc321_positive"
    violations = websec_findings(root, frozenset({FrameworkKind.FLASK}))
    matching = [v for v in violations if v.rule == "WEBSEC321"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"


# frob:tests src/frob/webapp/_websec_supply_chain.py::websec_findings kind="unit"
def test_websec_findings_discovery_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` returns `()` for an empty `frameworks` set
    without touching the filesystem, even over a fixture that would
    otherwise plant a WEBSEC321 finding."""
    root = _FIXTURE_ROOT / "webesc321_positive"
    assert websec_findings(root, frozenset()) == ()


# frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
def test_taint_gate_discovers_websec_supply_chain_hook() -> None:
    """POSITIVE CONTROL, end-to-end: `frob.gates._taint_gate.taint_gate`
    (T-5308's pkgutil-based discovery over every `frob.webapp._websec_*`
    module's `websec_findings` hook) finds and calls THIS module's hook
    without any `_taint_gate.py` edit, and reports the planted WEBSEC321
    finding in the fixture's real `Violation` output."""
    root = _FIXTURE_ROOT / "webesc321_positive"
    violations = taint_gate(root)
    matching = [v for v in violations if v.rule == "WEBSEC321"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "Dockerfile"
