"""Unit tests for errors_total/panics_contained_by/observe (T-0070, v0).

Covers docs/strata/policy.md#packs and docs/strata/boundary.md#v0-
implementation: node attr markers, the panics-supervisor reference check,
observe-generated Internal flows, the fixed log-class vocabulary, and the
"errors_total without observe" non-fatal diagnostic.
"""

from __future__ import annotations

import logging

from frob.strata import StrataError, elaborate, parse_module


def _elaborate(text: str):
    module = parse_module(text).danger_ok
    return elaborate(module)


class TestObservabilityHappyPath:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_errors_total_and_panics_become_node_attrs(self):
        text = """
        module m
        node supervisor : trusted
        node api : trusted {
            errors_total;
            panics_contained_by supervisor;
            observe { log error_paths, boundary_crossings; to obs_sink }
        }
        node obs_sink : trusted
        """
        model = _elaborate(text).danger_ok
        api = next(n for n in model.nodes if n.id == "api")
        assert "errors_total" in api.attrs
        assert "panics=supervisor" in api.attrs

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_observe_generates_internal_flow_to_target(self):
        text = """
        module m
        node api : trusted {
            observe { log state_transitions; to obs_sink }
        }
        node obs_sink : trusted
        """
        model = _elaborate(text).danger_ok
        obs_flow = next(f for f in model.flows if f.id == "api__obs")
        assert obs_flow.src == "api"
        assert obs_flow.dst == "obs_sink"
        assert obs_flow.label == "Internal"

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_errors_total_without_observe_is_non_fatal(self, caplog):
        text = """
        module m
        node api : trusted { errors_total; }
        """
        with caplog.at_level(logging.WARNING):
            result = _elaborate(text)
        assert result.is_ok
        assert any("errors_total without observe" in r.message for r in caplog.records)


class TestObservabilityFailClosed:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_panics_supervisor_must_be_declared(self):
        text = """
        module m
        node api : trusted { panics_contained_by nowhere; }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_observe_target_must_be_declared(self):
        text = """
        module m
        node api : trusted { observe { log error_paths; to nowhere } }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_unknown_log_class_is_rejected(self):
        text = """
        module m
        node obs_sink : trusted
        node api : trusted {
            observe { log not_a_real_class; to obs_sink }
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownLogClass


class TestEndToEnd:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:waive PERF003 reason="sibling next()-generator lookups over the elaborated model plus == assertions; not a nested join"
    def test_phases_operation_and_observe_together(self):
        text = """
        module m
        node gw : authenticated
        node session_store : trusted
        node audit_log : trusted { attr append_only; }
        node obs_sink : trusted
        node LedgerDb : trusted {
            errors_total;
            observe { log boundary_crossings, crash_events; to obs_sink }
        }
        node Balance : trusted
        flow f1 : gw -> gw
        boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified" {
            admit { rate_limit 20 req/min; max_size 64 KiB; }
            parse { time linear; frame {} }
            judge {}
            effect { frame { session_store } }
            record { audit to audit_log }
            refuse { respond Public; frame { audit_log } }
        }
        operation Transfer on LedgerDb {
            modifies { Balance(from), Balance(to) } on Ok;
            modifies {} on Err;
            atomic via LedgerDb
        }
        """
        module = parse_module(text).danger_ok
        model = elaborate(module).danger_ok

        assert any(f.id == "b1__effect_session_store" for f in model.flows)
        assert any(f.id == "b1__audit" for f in model.flows)
        assert any(f.id.startswith("Transfer__ok_") for f in model.flows)
        assert any(f.id == "LedgerDb__obs" for f in model.flows)

        from frob.strata import build_facts

        facts = build_facts(model)
        assert facts.is_ok
