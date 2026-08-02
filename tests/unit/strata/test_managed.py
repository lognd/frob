"""T-0172: the `managed` node/store marker -- config-only infrastructure
declared to have no scannable code (docs/strata/surface.md#node-grammar).

Two things are proved end to end (real `strata_core` parser, never a
hand-built `KernelModel`, mirroring `test_litmus_cwe.py`'s precedent):

1. `managed_vuln.strata`/`managed_hardened.strata` -- the SAME firing
   precondition and the SAME discharging claim/boundary shape (an ENDORSE
   boundary whose predicate does not match the catalog's required
   mitigation), but `db` is `managed` in the hardened twin only. The
   managed node discharges (the boundary-KIND proof is exempted); the
   non-managed node with the identical shape still fires undischarged.
2. `is_managed`/tier-2 import conformance: a `managed` node's owned files
   are skipped by `check_import_conformance`, the same way `FOREIGN` files
   are.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, elaborate, parse_module
from frob.strata._code_binding import (
    CodeBinding,
    check_import_conformance,
    is_managed,
)
from frob.strata._models import Node

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load_model(filename: str) -> KernelModel:
    """Parse+elaborate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text)
    assert module.is_ok, module.danger_err
    elaborated = elaborate(module.danger_ok)
    assert elaborated.is_ok, elaborated.danger_err
    return elaborated.danger_ok


class TestManagedGrammar:
    """The `managed` bare marker parses on both `node` and `store`."""

    # frob:tests strata-core/src/lib.rs::parse_source kind="unit"
    # frob:tests src/frob/strata/_code_binding.py::is_managed kind="unit"
    # frob:ticket T-0172
    def test_node_managed_marker_elaborates_to_attr(self):
        module = parse_module(
            'module m\nnode edge : trusted { managed; may "net.out:caddy"; }'
        ).danger_ok
        model = elaborate(module).danger_ok
        node = next(n for n in model.nodes if n.id == "edge")
        assert "managed" in node.attrs
        assert is_managed(node)

    # frob:tests strata-core/src/lib.rs::parse_source kind="unit"
    # frob:ticket T-0172
    def test_node_without_managed_is_not_managed(self):
        module = parse_module("module m\nnode edge : trusted").danger_ok
        model = elaborate(module).danger_ok
        node = next(n for n in model.nodes if n.id == "edge")
        assert "managed" not in node.attrs
        assert not is_managed(node)

    # frob:tests src/frob/strata/_infra.py::_elaborate_store kind="unit"
    # frob:ticket T-0172
    def test_store_managed_marker_elaborates_to_attr(self):
        module = parse_module("module m\nstore db : trusted { managed; }").danger_ok
        model = elaborate(module).danger_ok
        node = next(n for n in model.nodes if n.id == "db")
        assert "managed" in node.attrs
        assert is_managed(node)


class TestManagedDischargeFromParsedSurfaceSource:
    """T-0172: same shape, managed discharges / non-managed still fires."""

    # frob:tests src/frob/strata/_threat_discharge.py::check_discharge_completeness \
    # kind="unit"
    # frob:ticket T-0172
    def test_non_managed_node_with_mismatched_boundary_still_fires(self):
        from frob.strata._threat import check_discharge_completeness

        model = _load_model("managed_vuln.strata")
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = {(v.cwe, v.node): v for v in result.danger_ok}
        assert ("CWE-89", "db") in violations
        assert violations[("CWE-89", "db")].rule == "THREAT003"
        assert (
            "not of the required mitigation kind" in violations[("CWE-89", "db")].detail
        )

    # frob:tests src/frob/strata/_threat_discharge.py::check_discharge_completeness \
    # kind="unit"
    # frob:ticket T-0172
    def test_managed_node_with_same_shape_discharges(self):
        from frob.strata._threat import check_discharge_completeness

        model = _load_model("managed_hardened.strata")
        result = check_discharge_completeness(model)
        assert result.is_ok
        assert result.danger_ok == ()

    # frob:tests src/frob/strata/_threat_discharge.py::check_discharge_completeness \
    # kind="unit"
    # frob:ticket T-0172
    def test_managed_node_still_requires_a_discharging_claim(self):
        """Removing the claim from the managed fixture must still fire --
        `managed` exempts the boundary-KIND proof, not the obligation to
        discharge at all (docs/strata/surface.md#node-grammar: "obligations
        shift to config evidence or assumes", never "obligations vanish")."""
        from frob.strata._threat import check_discharge_completeness

        text = (_LITMUS_DIR / "managed_hardened.strata").read_text(encoding="utf-8")
        without_claim = "\n".join(
            line for line in text.splitlines() if "weakness:CWE-89:db" not in line
        )
        module = parse_module(without_claim).danger_ok
        model = elaborate(module).danger_ok
        result = check_discharge_completeness(model)
        assert result.is_ok
        violations = {(v.cwe, v.node) for v in result.danger_ok}
        assert ("CWE-89", "db") in violations


class TestManagedTier2ImportConformance:
    """`check_import_conformance` skips a managed node's owned files, the
    same way it already skips `FOREIGN` files (docs/strata/surface.md
    #code-binding-tier-2-v0-implementation)."""

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    # frob:ticket T-0172
    def test_managed_node_owned_files_produce_no_violation(self, tmp_path):
        # A managed node with a stray `code=` glob (should not happen in
        # practice, but "no tier-2 conformance" must hold even if one is
        # declared) that imports across an undeclared boundary -- an
        # ordinary node in this shape WOULD violate (see the sibling test
        # below); a managed one must not.
        (tmp_path / "edge").mkdir()
        (tmp_path / "edge" / "conf.py").write_text("import other.mod\n")
        (tmp_path / "other").mkdir()
        (tmp_path / "other" / "mod.py").write_text("x = 1\n")

        managed_node = Node(
            id="edge", trust="trusted", attrs=("managed", "code=edge/*.py")
        )
        other_node = Node(id="other", trust="trusted", attrs=("code=other/*.py",))
        model = KernelModel(nodes=(managed_node, other_node), flows=())
        binding = CodeBinding(owner={"edge/conf.py": "edge", "other/mod.py": "other"})
        report = check_import_conformance(model, binding, tmp_path)
        assert report.violations == ()

    # frob:tests src/frob/strata/_code_binding.py::check_import_conformance kind="unit"
    # frob:ticket T-0172
    def test_non_managed_node_with_same_shape_still_violates(self, tmp_path):
        (tmp_path / "edge").mkdir()
        (tmp_path / "edge" / "conf.py").write_text("import other.mod\n")
        (tmp_path / "other").mkdir()
        (tmp_path / "other" / "mod.py").write_text("x = 1\n")

        edge_node = Node(id="edge", trust="trusted", attrs=("code=edge/*.py",))
        other_node = Node(id="other", trust="trusted", attrs=("code=other/*.py",))
        model = KernelModel(nodes=(edge_node, other_node), flows=())
        binding = CodeBinding(owner={"edge/conf.py": "edge", "other/mod.py": "other"})
        report = check_import_conformance(model, binding, tmp_path)
        assert len(report.violations) == 1
        assert report.violations[0].src_component == "edge"
        assert report.violations[0].dst_component == "other"
