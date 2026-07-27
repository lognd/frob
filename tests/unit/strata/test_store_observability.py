"""T-0247: `errors_total`/`panics_contained_by`/`observe`/`on deploy` on
`store` -- surface.md's `store_prop := node_prop | ...` line implied these
were legal (`_ast.py::StoreDecl`'s own T-0247 comment confirmed the
grammar rejected them, same gap T-0166 closed for `code`/`may`), but
`strata-core/src/parse.rs::parse_store` had no branch for any of the four.
This proves the fix end to end (real `strata_core` parser, mirroring
`test_store_code_may.py`'s precedent): a store's errors_total/panics/
observe/deploy desugar onto the SAME `Node` fields/attrs
`_elaborate.py::_elaborate_node` uses for a `node`, and the SAME
`_elaborate.py::_validate_observability`/`_elaborate_observe_flows` checks
that walk `module.nodes` now also walk `module.stores`.
"""

from __future__ import annotations

import logging

from frob.strata import StrataError, elaborate, parse_module


def _elaborate(text: str):
    module = parse_module(text).danger_ok
    return elaborate(module)


class TestStoreObservabilityGrammar:
    """errors_total/panics_contained_by/observe parse on `store`, the same
    shape `node` has (T-0070's grammar, mirrored for store by T-0247)."""

    # frob:tests strata-core/src/lib.rs::parse_source kind="unit"
    # frob:tests src/frob/strata/_infra.py::_elaborate_store kind="unit"
    # frob:ticket T-0247
    # frob:waive DUP001 reason="parallel test fixtures across 3 sibling test file(s) \
    # (3 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case/per-scenario coverage; extracting would obscure per-case intent"
    def test_store_errors_total_and_panics_become_node_attrs(self):
        text = """
        module m
        node supervisor : trusted
        node obs_sink : trusted
        store db : trusted {
            errors_total;
            panics_contained_by supervisor;
            observe { log error_paths, boundary_crossings; to obs_sink }
        }
        """
        model = _elaborate(text).danger_ok
        db = next(n for n in model.nodes if n.id == "db")
        assert "errors_total" in db.attrs
        assert "panics=supervisor" in db.attrs

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:ticket T-0247
    # frob:waive DUP001 reason="parallel test fixtures across 2 sibling test file(s) \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case/per-scenario coverage; extracting would obscure per-case intent"
    def test_store_observe_generates_internal_flow_to_target(self):
        text = """
        module m
        node obs_sink : trusted
        store db : trusted {
            observe { log state_transitions; to obs_sink }
        }
        """
        model = _elaborate(text).danger_ok
        obs_flow = next(f for f in model.flows if f.id == "db__obs")
        assert obs_flow.src == "db"
        assert obs_flow.dst == "obs_sink"
        assert obs_flow.label == "Internal"

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:ticket T-0247
    # frob:waive DUP001 reason="parallel test fixtures across 2 sibling test file(s) \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case/per-scenario coverage; extracting would obscure per-case intent"
    def test_store_errors_total_without_observe_is_non_fatal(self, caplog):
        text = """
        module m
        store db : trusted { errors_total; }
        """
        with caplog.at_level(logging.WARNING):
            result = _elaborate(text)
        assert result.is_ok
        assert any("errors_total without observe" in r.message for r in caplog.records)


class TestStoreObservabilityFailClosed:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:ticket T-0247
    # frob:waive DUP001 reason="parallel test fixtures across 3 sibling test file(s) \
    # (7 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case/per-scenario coverage; extracting would obscure per-case intent"
    def test_store_panics_supervisor_must_be_declared(self):
        text = """
        module m
        store db : trusted { panics_contained_by nowhere; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:ticket T-0247
    # frob:waive DUP001 reason="parallel test fixtures across 3 sibling test file(s) \
    # (7 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case/per-scenario coverage; extracting would obscure per-case intent"
    def test_store_observe_target_must_be_declared(self):
        text = """
        module m
        store db : trusted { observe { log error_paths; to nowhere } }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:ticket T-0247
    # frob:waive DUP001 reason="parallel test fixtures across 2 sibling test file(s) \
    # (2 sites) sharing an arrange-act scaffold typical of exhaustive \
    # per-case/per-scenario coverage; extracting would obscure per-case intent"
    def test_store_unknown_log_class_is_rejected(self):
        text = """
        module m
        node obs_sink : trusted
        store db : trusted {
            observe { log not_a_real_class; to obs_sink }
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownLogClass


class TestStoreOnDeploy:
    """`on deploy { ... }` parses on `store` and lands on `Node.deploy` the
    same way it does for `node` (T-0136's contract, mirrored for store by
    T-0247)."""

    # frob:tests strata-core/src/lib.rs::parse_source kind="unit"
    # frob:tests src/frob/strata/_infra.py::_elaborate_store kind="unit"
    # frob:ticket T-0247
    def test_store_on_deploy_lands_on_node_deploy_contract(self):
        text = """
        module m
        boundary review_gate endorse artifact_flow : Public -> Internal
        node vault : trusted
        store db : trusted {
            on deploy {
                canary { authenticated for 10 min, trusted for 30 min };
                endorsed_by review_gate;
                rollback within 5 min;
            }
        }
        flow artifact_flow : vault -> db
        """
        model = _elaborate(text).danger_ok
        db = next(n for n in model.nodes if n.id == "db")
        assert db.deploy is not None
        assert [s.level for s in db.deploy.stages] == ["authenticated", "trusted"]
        assert db.deploy.endorsement_chain == ("review_gate",)
        assert db.deploy.rollback_budget.value == 5.0

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:ticket T-0247
    def test_store_without_on_deploy_leaves_node_deploy_none(self):
        model = _elaborate("module m\nstore db : trusted").danger_ok
        db = next(n for n in model.nodes if n.id == "db")
        assert db.deploy is None
