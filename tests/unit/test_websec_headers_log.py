"""frob.webapp._websec_headers_log coverage (T-5308): WEBSEC117-122
header/URL/log-injection and WebSocket origin/WSS-enforcement findings,
one positive + one negative fixture per rule id under
tests/fixtures/webapp/websec1xx/headers_log/.

Gate wiring is the `websec_findings(root, frameworks) -> tuple[Violation,
...]` module-level hook `frob.gates._taint_gate.taint_gate` auto-
discovers from every `frob.webapp._websec_*` module (T-5308's discovery
mechanism, added directly to `_taint_gate.py` once T-5311's own lease on
that file freed) -- `test_websec_findings_hook_*` below cover the hook
directly, and `TestTaintGateDiscovery` covers the discovery mechanism
end to end, including a planted fake `frob.webapp._websec_*` module.

frob:ticket T-5308
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

import frob.webapp
from frob.gates._taint_gate import taint_gate
from frob.webapp._detect import detect_frameworks
from frob.webapp._websec_headers_log import (
    websec_findings,
    websec_headers_log_findings,
)

_FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "webapp"
    / "websec1xx"
    / "headers_log"
)

_CASES = [
    ("websec117_positive", "WEBSEC117", True),
    ("websec117_negative", "WEBSEC117", False),
    ("websec118_positive", "WEBSEC118", True),
    ("websec118_negative", "WEBSEC118", False),
    ("websec119_positive", "WEBSEC119", True),
    ("websec119_negative", "WEBSEC119", False),
    ("websec120_positive", "WEBSEC120", True),
    ("websec120_negative", "WEBSEC120", False),
    ("websec121_positive", "WEBSEC121", True),
    ("websec121_negative", "WEBSEC121", False),
    ("websec122_positive", "WEBSEC122", True),
    ("websec122_negative", "WEBSEC122", False),
]


# frob:tests src/frob/webapp/_websec_headers_log.py::WebsecHeaderLogFinding kind="unit"
@pytest.mark.parametrize("fixture_dir,rule,expect_finding", _CASES)
# frob:tests src/frob/webapp/_websec_headers_log.py::websec_headers_log_findings \
# kind="unit"
def test_websec_headers_log_findings_fixture(
    fixture_dir: str, rule: str, expect_finding: bool
) -> None:
    """MUST-FIRE: each rule's positive fixture plants at least that rule
    id; the matching negative fixture (encoded/validated value) fires
    nothing for that rule."""
    root = _FIXTURE_ROOT / fixture_dir
    findings = websec_headers_log_findings(root)
    matching = [f for f in findings if f.rule == rule]
    if expect_finding:
        assert len(matching) >= 1, findings
    else:
        assert matching == [], findings


# frob:tests src/frob/webapp/_websec_headers_log.py::websec_headers_log_findings \
# kind="unit"
def test_websec_headers_log_findings_no_framework_short_circuits(
    tmp_path: Path,
) -> None:
    """A plain, non-web-framework directory scans nothing (T-5302's
    detect_frameworks contract), even if it happens to contain a `.py`
    file that would otherwise plant a WEBSEC117 finding."""
    (tmp_path / "views.py").write_text(
        'response.setHeader("X-Redirect-To", request.args["next"])\n',
        encoding="utf-8",
    )
    assert websec_headers_log_findings(tmp_path) == ()


# frob:tests src/frob/webapp/_websec_headers_log.py::websec_findings kind="unit"
def test_websec_findings_hook_emits_gate_violation() -> None:
    """MUST-FIRE (positive control): T-5311's `taint_gate` module-
    discovery hook, called the way `taint_gate` calls it (with the
    caller's own already-computed `detect_frameworks` result), turns the
    WEBSEC117 fixture into one WARN-tier `Violation`."""
    root = _FIXTURE_ROOT / "websec117_positive"
    frameworks = detect_frameworks(root)
    assert frameworks
    violations = websec_findings(root, frameworks)
    matching = [v for v in violations if v.rule == "WEBSEC117"]
    assert len(matching) == 1, violations
    assert matching[0].severity.value == "warn"
    assert matching[0].file == "views.py"


# frob:tests src/frob/webapp/_websec_headers_log.py::websec_findings kind="unit"
def test_websec_findings_hook_empty_frameworks_short_circuits() -> None:
    """`websec_findings` never re-detects frameworks itself -- an empty
    `frameworks` set (the caller's own `detect_frameworks` result) short-
    circuits to `()` even for a fixture directory that would otherwise
    plant a finding."""
    root = _FIXTURE_ROOT / "websec117_positive"
    assert websec_findings(root, frozenset()) == ()


class TestTaintGateDiscovery:
    """`frob.gates._taint_gate.taint_gate`'s `frob.webapp._websec_*`
    hook-discovery mechanism (T-5308)."""

    # frob:tests src/frob/gates/_taint_gate.py::taint_gate kind="unit"
    def test_taint_gate_emits_websec117_violation(self, tmp_path: Path) -> None:
        """MUST-FIRE (positive control): a real git repo with a Django
        framework marker plus one request-derived, unsanitized response
        header assignment produces a `WEBSEC117` `Violation` through
        `taint_gate` end to end -- discovery finds
        `_websec_headers_log.websec_findings` with no hard-coded
        `_taint_gate.py` call site for this rule family."""
        import subprocess as sp

        sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        sp.run(
            ["git", "config", "user.email", "t@example.com"], cwd=tmp_path, check=True
        )
        sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
        (tmp_path / "manage.py").write_text("import django\n", encoding="utf-8")
        (tmp_path / "views.py").write_text(
            "def handle(request, response):\n"
            '    response.setHeader("X-Redirect-To", request.args["next"])\n',
            encoding="utf-8",
        )
        sp.run(["git", "add", "."], cwd=tmp_path, check=True)
        sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

        violations = taint_gate(tmp_path)
        websec = [v for v in violations if v.rule == "WEBSEC117"]
        assert len(websec) == 1
        assert websec[0].severity.value == "warn"
        assert websec[0].file == "views.py"

    # frob:tests src/frob/gates/_taint_gate.py::_discover_websec_hook_modules \
    # kind="unit"
    def test_discovery_finds_a_planted_fake_module(
        self, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        """A fake `_websec_zzz_fake.py` module file exposing
        `websec_findings(root, frameworks)`, added to `frob.webapp`'s own
        `__path__` for the duration of the test, is discovered and
        called by `taint_gate` alongside every real WEBSEC family --
        proves discovery is genuinely dynamic (`pkgutil.iter_modules` +
        `importlib` over the real package path), not a hard-coded list
        of today's known modules."""
        fake_pkg_dir = tmp_path_factory.mktemp("fake_websec_pkg")
        (fake_pkg_dir / "_websec_zzz_fake.py").write_text(
            "from frob.findings import Severity, Violation\n"
            "\n"
            "\n"
            "def websec_findings(root, frameworks):\n"
            "    if not frameworks:\n"
            "        return ()\n"
            "    return (\n"
            "        Violation(\n"
            '            rule="WEBSEC999",\n'
            "            severity=Severity.WARN,\n"
            '            file="planted.py",\n'
            "            line=1,\n"
            '            message="WEBSEC999: planted fake finding for discovery coverage",\n'
            "        ),\n"
            "    )\n",
            encoding="utf-8",
        )
        module_name = "frob.webapp._websec_zzz_fake"
        frob.webapp.__path__.append(str(fake_pkg_dir))
        try:
            import subprocess as sp

            sp.run(["git", "init", "-q"], cwd=tmp_path, check=True)
            sp.run(
                ["git", "config", "user.email", "t@example.com"],
                cwd=tmp_path,
                check=True,
            )
            sp.run(["git", "config", "user.name", "t"], cwd=tmp_path, check=True)
            (tmp_path / "manage.py").write_text("import django\n", encoding="utf-8")
            sp.run(["git", "add", "."], cwd=tmp_path, check=True)
            sp.run(["git", "commit", "-q", "-m", "init"], cwd=tmp_path, check=True)

            violations = taint_gate(tmp_path)
        finally:
            frob.webapp.__path__.remove(str(fake_pkg_dir))
            sys.modules.pop(module_name, None)

        planted = [v for v in violations if v.rule == "WEBSEC999"]
        assert len(planted) == 1, violations
