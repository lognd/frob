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


# frob:ticket T-2407
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

    # frob:ticket T-2407
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
        # T-2407: SYS003 promoted WARN -> ERROR once the last real
        # findings (post-T-2380/T-2403 calibration) were burned to zero.
        assert sys003[0].severity.name == "ERROR"


# frob:ticket T-2407
class TestSys003DeclaredPairDoesNotMaskReverse:
    """T-2403's own lesson, caught mid-ticket: `Flow` declarations are
    per NODE PAIR, not per import site -- declaring `A -> B` for one
    legitimate, narrow need silently permits EVERY OTHER `A -> B` import
    too, including ones that are real drift. A `gates -> cli` declaration
    intended only to cover the WIRE gate's genuine need to introspect the
    live CLI parser was caught, mid-implementation, ALSO permitting an
    unrelated `frob.app.config.load_arch_config` import that should have
    stayed flagged -- both were filed as drift together instead. This
    test is the generalized regression: declaring `A -> B` must still
    catch `B -> A` (the reverse direction), proving a declared edge does
    not accidentally widen into a bidirectional pass."""

    def test_declared_forward_edge_does_not_permit_the_reverse(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        import frob.strata as strata_mod

        nodes = (
            Node(id="a", trust="trusted", attrs=("code=pkg_a/*.py",)),
            Node(id="b", trust="trusted", attrs=("code=pkg_b/*.py",)),
        )
        # Only a -> b is declared, mirroring T-2403's real shape.
        flows = (Flow(id="f_a_b", src="a", dst="b"),)
        model = KernelModel(nodes=nodes, flows=flows)
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        _write(tmp_path, "design/.gitkeep", "")
        # The declared direction: silent.
        _write(tmp_path, "pkg_a/mod.py", "import pkg_b.mod\n")
        # The reverse, undeclared direction: must still fire.
        _write(tmp_path, "pkg_b/other.py", "import pkg_a.mod\n")
        _write(tmp_path, "pkg_b/mod.py", "x = 1\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = [v for v in violations if v.rule == "SYS003"]
        assert len(sys003) == 1
        assert sys003[0].file == "pkg_b/other.py"

    # frob:ticket T-2407
    def test_declared_pair_does_not_mask_a_third_node_reaching_the_same_dst(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """T-2407's own carried-forward instance of the same lesson: a
        Flow is scoped to its declared (src, dst) pair only, so declaring
        `a -> b` must not silence an UNRELATED `c -> b` import that
        shares only the destination node. This is the shape T-2407 had
        to rule out by hand (`git grep` across each source node's whole
        code glob) before adding each of its four Flows -- a component
        importing the same widely-depended-on node (like this repo's
        `cli`) from a second, undeclared source must still fire."""
        import frob.strata as strata_mod

        nodes = (
            Node(id="a", trust="trusted", attrs=("code=pkg_a/*.py",)),
            Node(id="b", trust="trusted", attrs=("code=pkg_b/*.py",)),
            Node(id="c", trust="trusted", attrs=("code=pkg_c/*.py",)),
        )
        # Only a -> b is declared; c -> b has no Flow at all.
        flows = (Flow(id="f_a_b", src="a", dst="b"),)
        model = KernelModel(nodes=nodes, flows=flows)
        monkeypatch.setattr(
            strata_mod,
            "load_design_ids",
            lambda root, design_dir: DesignIds(models=(model,)),
        )
        _write(tmp_path, "design/.gitkeep", "")
        # The declared direction: silent.
        _write(tmp_path, "pkg_a/mod.py", "import pkg_b.mod\n")
        # A different source importing the same dst, undeclared: must fire.
        _write(tmp_path, "pkg_c/mod.py", "import pkg_b.mod\n")
        _write(tmp_path, "pkg_b/mod.py", "x = 1\n")
        snapshot = _snapshot(tmp_path)
        violations = sys_gate(tmp_path, snapshot)
        sys003 = [v for v in violations if v.rule == "SYS003"]
        assert len(sys003) == 1
        assert sys003[0].file == "pkg_c/mod.py"


# frob:ticket T-2407
class TestSys003ZeroOnFrobsOwnRepo:
    """T-2407's own closure-bar evidence: `frob check --only sys`'s SYS003
    family, run against THIS repo's own live `design/frob.strata`, reports
    zero findings -- the epic's (T-0969) acceptance criterion [0]. Filters
    specifically to `rule == "SYS003"` rather than asserting the whole
    `sys_gate` output is empty: `tests/system/test_frob_self_model.py::
    TestFrobSelfModel::test_sys_gate_zero_violations` asserts a broader,
    pre-existing (and, as of this writing, already-failing on `main` for
    reasons outside T-2407's scope) zero-ALL-violations bar that also
    covers the unrelated SELFAUDIT/SYS100/SYS101/SYS111 self-audit
    families; this test isolates the one family T-2407 actually owns."""

    def test_sys003_zero_against_live_repo_design(self, tmp_path: Path) -> None:
        from frob.gates import sys_gate
        from frob.graph import build_graph

        repo_root = Path(__file__).resolve().parents[3]
        build_result = build_graph(repo_root, tmp_path / "cache.db")
        assert build_result.is_ok, f"graph build failed: {build_result.err}"
        violations = sys_gate(repo_root, build_result.danger_ok)
        sys003 = [v for v in violations if v.rule == "SYS003"]
        assert sys003 == [], f"unexpected SYS003 finding(s): {sys003}"
