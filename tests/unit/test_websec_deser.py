"""frob.webapp._websec_deser coverage (T-5309): WEBSEC109-116
code-injection and unsafe-deserialization sink findings, one positive +
one negative fixture per sink kind under
tests/fixtures/webapp/websec1xx/deser/, plus the `websec_findings(root,
frameworks)` gate-discovery hook (T-5311) `frob.gates._taint_gate` binds
against.

frob:ticket T-5309
"""

from __future__ import annotations

import subprocess as sp
from pathlib import Path

import pytest

from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import FrameworkKind, detect_frameworks
from frob.webapp._websec_deser import websec_deser_findings, websec_findings

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1] / "fixtures" / "webapp" / "websec1xx" / "deser"
)

_CASES = [
    ("webesc109_positive", "WEBSEC109", True),
    ("webesc109_negative", "WEBSEC109", False),
    ("webesc110_positive", "WEBSEC110", True),
    ("webesc110_negative", "WEBSEC110", False),
    ("webesc111_positive", "WEBSEC111", True),
    ("webesc111_negative", "WEBSEC111", False),
    ("webesc112_positive", "WEBSEC112", True),
    ("webesc112_negative", "WEBSEC112", False),
    ("webesc113_positive", "WEBSEC113", True),
    ("webesc113_negative", "WEBSEC113", False),
    ("webesc114_positive", "WEBSEC114", True),
    ("webesc114_negative", "WEBSEC114", False),
    ("webesc115_positive", "WEBSEC115", True),
    ("webesc115_negative", "WEBSEC115", False),
    ("webesc116_positive", "WEBSEC116", True),
    ("webesc116_negative", "WEBSEC116", False),
]


# frob:tests src/frob/webapp/_websec_deser.py::WebsecDeserFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_deser.py::websec_deser_findings kind="unit"
def test_websec_deser_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each sink's positive fixture plants exactly that rule id;
    the matching negative fixture (literal/sanitized value) fires nothing."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_deser_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) == 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_deser.py::websec_deser_findings kind="unit"
def test_websec_deser_findings_no_framework_short_circuits(tmp_path: Path) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a `.py`
    file that would otherwise plant a WEBSEC110 finding."""
    (tmp_path / "app.py").write_text(
        "def handler(user_expr):\n    return eval(user_expr)\n", encoding="utf-8"
    )
    assert websec_deser_findings(tmp_path) == ()


class TestWebsecFindingsGateHook:
    """`websec_findings(root, frameworks)` (T-5311's gate-discovery hook
    contract) emits the same WEBSEC109-116 findings as
    `websec_deser_findings`, as `Violation`s, gated by the CALLER-supplied
    `frameworks` rather than re-running `detect_frameworks` itself."""

    # frob:tests src/frob/webapp/_websec_deser.py::websec_findings kind="unit"
    def test_websec_findings_emits_violation(self, tmp_path: Path) -> None:
        """A real git repo with a framework marker plus one unsanitized
        `eval(...)` call produces a `WEBSEC110` `Violation`."""
        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(
            ["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True
        )
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
        (tmp_path / "app.py").write_text(
            "def handler(user_expr):\n    return eval(user_expr)\n", encoding="utf-8"
        )
        sp.run(["git", "add", "."], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

        frameworks = detect_frameworks(tmp_path)
        violations = websec_findings(tmp_path, frameworks)
        deser = [v for v in violations if v.rule == "WEBSEC110"]
        assert len(deser) == 1
        assert deser[0].severity.value == "warn"
        assert deser[0].file == "app.py"

    # frob:tests src/frob/webapp/_websec_deser.py::websec_findings kind="unit"
    def test_websec_findings_short_circuits_on_empty_frameworks(
        self, tmp_path: Path
    ) -> None:
        """`websec_findings` trusts the caller's `frameworks` argument --
        an empty frozenset scans nothing even if the directory would
        otherwise plant a finding."""
        (tmp_path / "app.py").write_text(
            "def handler(user_expr):\n    return eval(user_expr)\n", encoding="utf-8"
        )
        assert websec_findings(tmp_path, frozenset[FrameworkKind]()) == ()


class TestTaintGateDiscoversWebsecDeser:
    """`frob.gates._taint_gate.taint_gate` (T-5308's `pkgutil`-based
    discovery mechanism) finds this module's `websec_findings` hook with
    no hand-edit to `_taint_gate.py` -- MUST-FIRE positive control against
    the real gate entrypoint, not just this module's own function."""

    # frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
    def test_taint_gate_reports_planted_webesc110_fixture(self) -> None:
        """The committed `webesc110_positive` fixture (tracked in THIS
        repo's own git history) plants exactly one WEBSEC110 finding when
        scanned through the real `taint_gate` entrypoint."""
        root = _FIXTURE_ROOT / "webesc110_positive"
        violations = taint_gate(root)
        matching = [v for v in violations if v.rule == "WEBSEC110"]
        assert len(matching) == 1, violations
        assert matching[0].severity.value == "warn"
