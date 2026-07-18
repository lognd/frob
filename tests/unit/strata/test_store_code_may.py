"""T-0166: `code`/`may` on `store` -- surface.md's `store_prop := node_prop
| ...` line implied these were legal (`_ast.py::StoreDecl`'s own T-0150
comment confirmed the grammar rejected them), but `strata-core/src/parse.rs
::parse_store` had no `code`/`may` branch. This proves the fix end to end
(real `strata_core` parser, mirroring `test_managed.py`'s precedent): a
store's `code` binds source and participates in tier-2 import conformance
exactly like a code-modeled node's would, and a store's `may` capability
feeds THREAT003 weakness obligations exactly like a node's would --
`_infra.py::_elaborate_store` desugars both onto the SAME `Node` fields
`_elaborate.py::_elaborate_node` uses, so every downstream consumer
(`_code_binding.py`, `_threat.py`) reads them with no store/node
distinction.
"""

from __future__ import annotations

from frob.strata import KernelModel, Node, elaborate, parse_module
from frob.strata._code_binding import _node_code_globs
from frob.strata._threat import (
    CWE_CATALOG,
    CWE_TOP_25_CATALOG,
    check_discharge_completeness,
)


class TestStoreCodeMayGrammar:
    """`code`/`may` parse on `store`, the same STRING+/STRING shape `node` has."""

    # frob:tests strata-core/src/lib.rs::parse_source kind="unit"
    # frob:tests src/frob/strata/_infra.py::_elaborate_store kind="unit"
    # frob:ticket T-0166
    def test_store_code_glob_elaborates_to_code_attr(self):
        module = parse_module(
            'module m\nstore db : trusted { code "src/frob/tickets/**"; }'
        ).danger_ok
        model = elaborate(module).danger_ok
        node = next(n for n in model.nodes if n.id == "db")
        assert "code=src/frob/tickets/**" in node.attrs
        assert _node_code_globs(node) == ("src/frob/tickets/**",)

    # frob:tests strata-core/src/lib.rs::parse_source kind="unit"
    # frob:tests src/frob/strata/_infra.py::_elaborate_store kind="unit"
    # frob:ticket T-0166
    def test_store_may_capability_lands_on_node_may(self):
        module = parse_module(
            'module m\nstore db : trusted { may "exec"; may "fs"; }'
        ).danger_ok
        model = elaborate(module).danger_ok
        node = next(n for n in model.nodes if n.id == "db")
        assert node.may == ("exec", "fs")

    # frob:tests strata-core/src/lib.rs::parse_source kind="unit"
    # frob:ticket T-0166
    def test_store_without_code_or_may_defaults_empty(self):
        module = parse_module("module m\nstore db : trusted").danger_ok
        model = elaborate(module).danger_ok
        node = next(n for n in model.nodes if n.id == "db")
        assert not node.may
        assert _node_code_globs(node) == ()


class TestStoreMayFeedsThreat003:
    """A store's `may` atom auto-instantiates a THREAT003 obligation the
    same way a node's would -- `_threat.py::check_discharge_completeness`
    reads `Node.may` generically, with no provenance distinction."""

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0166
    def test_store_with_exec_may_fires_undischarged_cwe_94(self):
        module = parse_module('module m\nstore db : trusted { may "exec"; }').danger_ok
        model = elaborate(module).danger_ok
        result = check_discharge_completeness(
            model, catalog=CWE_CATALOG + CWE_TOP_25_CATALOG
        )
        assert result.is_ok
        violations = {v.cwe: v for v in result.danger_ok}
        assert "CWE-94" in violations
        assert violations["CWE-94"].node == "db"
        assert violations["CWE-94"].rule == "THREAT003"

    # frob:tests src/frob/strata/_threat.py::check_discharge_completeness kind="unit"
    # frob:ticket T-0166
    def test_store_without_may_fires_no_obligation(self):
        model = KernelModel(nodes=(Node(id="db", trust="trusted"),))
        result = check_discharge_completeness(
            model, catalog=CWE_CATALOG + CWE_TOP_25_CATALOG
        )
        assert result.is_ok
        assert not result.danger_ok
