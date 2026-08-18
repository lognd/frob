"""T-2380 SYS003 calibration regression coverage.

The 2026-08-18 measurement found 4834 SYS003 findings, 95.4% (4610) of
which were `testsuite -> *` -- a test file importing the production
module it exercises, the expected shape of a test suite, not real
architecture drift. The fix declared here is a Flow per (testsuite,
component) pair actually observed in this repo's own test suite
(`design/frob.strata`), NOT a `testsuite -> *` wildcard exemption baked
into the gate itself -- a blanket exemption matching the normal case
would DISABLE the guard for that whole direction (the exact T-1967
failure shape: an exemption that matches the normal case is a deletion,
not an exemption).

This module proves the narrowing is safe using frob.strata's own Python
model-construction API directly (the same pattern
`tests/test_gates.py::TestSysGate::test_sys003_import` already uses,
since the surface grammar does not lex `code=`/`flow` declarations for
ad-hoc synthetic models): a `testsuite -> declared` edge with a Flow must
be silent, but the gate must still fire on (a) `production -> testsuite`
(a real defect class), and (b) `testsuite -> undeclared` (a component
with no Flow, proving this is a set of explicit declared edges, not a
blanket pass for the whole direction).
"""

from __future__ import annotations

from pathlib import Path

from frob.gates import sys_gate
from frob.graph import build_graph
from frob.strata import DesignIds, Flow, KernelModel, Node


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs -- local twin of
    `tests/test_gates.py::_write` (kept local so this module has no
    import-time coupling to that file's fixture-heavy module body)."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _snapshot(root: Path):
    """Build a fresh graph snapshot for `sys_gate`, local twin of
    `tests/test_gates.py::_snapshot`."""
    cache = root / ".frob" / "cache.db"
    return build_graph(root, cache).danger_ok


class TestSys003TestsuiteFlowCalibration:
    """Positive control for the T-2380 model fix: proves the narrowing
    keeps SYS003 capable of firing on every violation class it must, and
    is silent only for the specific declared edges."""

    def _model(self, monkeypatch, *, declare_flow: bool) -> None:
        import frob.strata as strata_mod

        nodes = (
            Node(id="testsuite", trust="trusted", attrs=("code=tests/*.py",)),
            Node(id="prod_a", trust="trusted", attrs=("code=src_a/*.py",)),
            Node(id="prod_b", trust="trusted", attrs=("code=src_b/*.py",)),
        )
        flows = ()
        if declare_flow:
            flows = (Flow(id="f_testsuite_prod_a", src="testsuite", dst="prod_a"),)
        model = KernelModel(nodes=nodes, flows=flows)
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )

    def test_must_now_be_silent__testsuite_importing_declared_tested_module(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A normal test importing the production module it exercises,
        with the testsuite->prod_a Flow declared: SYS003 must NOT fire.
        This is the exact shape 4610 of the original 4834 findings were."""
        self._model(monkeypatch, declare_flow=True)
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "tests/test_a.py", "import src_a.mod\n")
        _write(tmp_path, "src_a/mod.py", "x = 1\n")
        _write(tmp_path, "src_b/mod.py", "y = 2\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = [v for v in violations if v.rule == "SYS003"]
        assert sys003 == []

    def test_must_still_fire__testsuite_importing_undeclared_component(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The declared Flow above names testsuite->prod_a ONLY. A test
        importing prod_b (no Flow declared toward it) must still fire --
        proof this is a set of explicit declared edges, not a `testsuite
        -> *` wildcard that would silently swallow every future direction
        too."""
        self._model(monkeypatch, declare_flow=True)
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "tests/test_b.py", "import src_b.mod\n")
        _write(tmp_path, "src_a/mod.py", "x = 1\n")
        _write(tmp_path, "src_b/mod.py", "y = 2\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = [v for v in violations if v.rule == "SYS003"]
        assert len(sys003) == 1
        assert sys003[0].file == "tests/test_b.py"

    def test_must_still_fire__production_importing_testsuite(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The reverse direction (a production module importing test
        code) is a real defect class T-2380's fix must never silence --
        no Flow was declared prod_a->testsuite, before or after this
        change, so it must still fire."""
        self._model(monkeypatch, declare_flow=True)
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "src_a/mod.py", "import tests.fixture_helper\n")
        _write(tmp_path, "tests/fixture_helper.py", "z = 3\n")
        _write(tmp_path, "src_b/mod.py", "y = 2\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = [v for v in violations if v.rule == "SYS003"]
        assert len(sys003) == 1
        assert sys003[0].file == "src_a/mod.py"

    def test_must_still_fire__genuine_undeclared_production_cross_import(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Baseline sanity, independent of the testsuite direction
        entirely: a genuine undeclared production-to-production import
        (prod_a -> prod_b, no Flow either direction) must fire both
        before and after this ticket's model changes -- this test never
        touches the testsuite Flow at all, so it is a stable must-still-
        fire fixture the calibration work cannot accidentally weaken."""
        self._model(monkeypatch, declare_flow=False)
        _write(tmp_path, "design/.gitkeep", "")
        _write(tmp_path, "src_a/mod.py", "import src_b.mod\n")
        _write(tmp_path, "src_b/mod.py", "y = 2\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = [v for v in violations if v.rule == "SYS003"]
        assert len(sys003) == 1
        assert sys003[0].file == "src_a/mod.py"
        assert sys003[0].severity.name == "WARN"
