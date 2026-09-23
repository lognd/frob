"""frob.webapp._websec_bounds / frob.gates._taint_gate coverage (T-5311):
WEBSEC123-125 resource-exhaustion input-bounds findings, one positive +
one negative fixture per rule id under
tests/fixtures/webapp/websec1xx/bounds/.

frob:ticket T-5311
"""

from __future__ import annotations

import subprocess as sp
from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._websec_bounds import websec_bounds_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec1xx" / "bounds"
)

_CASES = [
    ("webesc123_positive", "WEBSEC123", True),
    ("webesc123_negative", "WEBSEC123", False),
    ("webesc124_positive", "WEBSEC124", True),
    ("webesc124_negative", "WEBSEC124", False),
    ("webesc125_positive", "WEBSEC125", True),
    ("webesc125_negative", "WEBSEC125", False),
]


# frob:tests src/frob/webapp/_websec_bounds.py::WebsecBoundsFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_bounds.py::websec_bounds_findings kind="unit"
def test_websec_bounds_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants exactly that rule id;
    the matching negative fixture (bounded/guarded shape) fires nothing."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_bounds_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_bounds.py::websec_bounds_findings kind="unit"
def test_websec_bounds_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a `.py`
    file that would otherwise plant a WEBSEC125 finding."""
    (tmp_path / "recurse.py").write_text(
        "def walk(node):\n    for c in node.children:\n        walk(c)\n",
        encoding="utf-8",
    )
    assert websec_bounds_findings(tmp_path) == ()


class TestTaintGateWebsecBoundsExtension:
    """`frob.gates._taint_gate.taint_gate` folds WEBSEC123-125 findings in
    alongside its own SEC005 and WEBSEC101-106 scans (T-5311)."""

    # frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
    def test_taint_gate_emits_websec_bounds_violation(self, tmp_path: Path) -> None:
        """A real git repo with a framework marker plus one unbounded-
        recursion function produces a `WEBSEC125` `Violation`."""
        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(
            ["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True
        )
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "requirements.txt").write_text("fastapi\n", encoding="utf-8")
        (tmp_path / "recurse.py").write_text(
            "def process_tree(node):\n"
            "    for child in node.children:\n"
            "        process_tree(child)\n",
            encoding="utf-8",
        )
        sp.run(["git", "add", "."], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

        violations = taint_gate(tmp_path)
        bounds = [v for v in violations if v.rule == "WEBSEC125"]
        assert len(bounds) == 1
        assert bounds[0].severity.value == "warn"
        assert bounds[0].file == "recurse.py"


# frob:todo T-5311 item 28 (business-logic step-skipping) is dynamic-only
# per the T-5141 corpus -- no static AST/regex shape detects "a multi-step
# checkout/workflow endpoint reachable out of order". A real detector needs
# either a runtime/integration harness that drives the step sequence out of
# order and observes the response, or a route-graph model of declared step
# ordering (COMPLY/authz family territory, T-5356) checked against actual
# handler reachability -- neither exists yet. Filed as a follow-up dynamic-
# test obligation rather than a static WEBSEC12x rule.
