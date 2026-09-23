"""frob.webapp._websec_sinks / frob.gates._taint_gate coverage (T-5307):
WEBSEC101-106 DOM/template XSS sink findings, one positive + one negative
fixture per sink kind under tests/fixtures/webapp/websec1xx/.

frob:ticket T-5307
"""

from __future__ import annotations

import subprocess as sp
from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._websec_sinks import websec_sink_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec1xx"
)

_CASES = [
    ("webesc101_positive", "WEBSEC101", True),
    ("webesc101_negative", "WEBSEC101", False),
    ("webesc102_positive", "WEBSEC102", True),
    ("webesc102_negative", "WEBSEC102", False),
    ("webesc103_positive", "WEBSEC103", True),
    ("webesc103_negative", "WEBSEC103", False),
    ("webesc104_positive", "WEBSEC104", True),
    ("webesc104_negative", "WEBSEC104", False),
    ("webesc105_positive", "WEBSEC105", True),
    ("webesc105_negative", "WEBSEC105", False),
    ("webesc106_positive", "WEBSEC106", True),
    ("webesc106_negative", "WEBSEC106", False),
]


# frob:tests src/frob/webapp/_websec_sinks.py::WebsecSinkFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_sinks.py::websec_sink_findings kind="unit"
def test_websec_sink_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each sink's positive fixture plants exactly that rule id;
    the matching negative fixture (literal/sanitized value) fires nothing."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_sink_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_sinks.py::websec_sink_findings kind="unit"
def test_websec_sink_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a `.js`
    file that would otherwise plant a WEBSEC101 finding."""
    (tmp_path / "app.js").write_text("el.innerHTML = userComment;\n", encoding="utf-8")
    assert websec_sink_findings(tmp_path) == ()


class TestTaintGateWebsecExtension:
    """`frob.gates._taint_gate.taint_gate` folds WEBSEC101-106 findings in
    alongside its own SEC005 scan (T-5307)."""

    # frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
    def test_taint_gate_emits_websec_violation(self, tmp_path: Path) -> None:
        """A real git repo with a framework marker plus one unsanitized
        `.innerHTML` assignment produces a `WEBSEC101` `Violation`."""
        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(
            ["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True
        )
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "vite.config.js").write_text(
            "export default {};\n", encoding="utf-8"
        )
        (tmp_path / "app.js").write_text(
            "export function render(el, userComment) {\n"
            "  el.innerHTML = userComment;\n"
            "}\n",
            encoding="utf-8",
        )
        sp.run(["git", "add", "."], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

        violations = taint_gate(tmp_path)
        websec = [v for v in violations if v.rule == "WEBSEC101"]
        assert len(websec) == 1
        assert websec[0].severity.value == "warn"
        assert websec[0].file == "app.js"
