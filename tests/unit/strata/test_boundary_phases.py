"""Unit tests for six-phase boundaries + outcome-conditioned frames (T-0069).

Covers docs/strata/boundary.md#v0-implementation: the phase-block grammar,
the admit/parse-frame-must-be-empty rule, the refuse-frame audit-only
rule, error-response labeling, the `record` audit flow, the `effect`
outcome-conditioned flows, and the `operation` strong-guarantee /
cross-store-atomicity check.
"""

from __future__ import annotations

from frob.strata import Outcome, StrataError, elaborate, parse_module


def _elaborate(text: str):
    module = parse_module(text).danger_ok
    return elaborate(module)


class TestPhaseBlockHappyPath:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_effect_and_record_phases_generate_flows(self):
        text = """
        module m
        node gw : authenticated
        node session_store : trusted
        node audit_log : trusted { attr append_only; }
        flow f1 : gw -> gw
        boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified" {
            admit { rate_limit 20 req/min; max_size 64 KiB; }
            parse { time linear; frame {} }
            judge {}
            effect { frame { session_store } }
            record { audit to audit_log }
            refuse { respond Public; frame { audit_log } }
        }
        """
        model = _elaborate(text).danger_ok
        effect_flow = next(f for f in model.flows if f.id == "b1__effect_session_store")
        assert effect_flow.src == "gw"
        assert effect_flow.dst == "session_store"
        assert effect_flow.condition is not None
        assert effect_flow.condition.outcome is Outcome.OK

        audit_flow = next(f for f in model.flows if f.id == "b1__audit")
        assert audit_flow.dst == "audit_log"
        assert audit_flow.label == "Internal"

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_boundary_without_phases_still_elaborates(self):
        text = """
        module m
        flow f1 : a -> b
        boundary b1 endorse f1 : foreign -> authenticated
        """
        model = _elaborate(text).danger_ok
        assert model.boundaries[0].id == "b1"


class TestPhaseBlockFailClosed:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:waive DUP001 reason="parallel test methods within \
    # test_boundary_phases.py (2 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_parse_phase_frame_must_be_empty(self):
        text = """
        module m
        node gw : authenticated
        node x : trusted
        flow f1 : gw -> gw
        boundary b1 endorse f1 : foreign -> authenticated {
            parse { frame { x } }
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.FrameViolation

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:waive DUP001 reason="parallel test fixtures across 3 sibling \
    # test file(s) (7 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case/per-scenario coverage; extracting would obscure \
    # per-case intent"
    def test_effect_frame_target_must_be_declared(self):
        text = """
        module m
        flow f1 : a -> b
        boundary b1 endorse f1 : foreign -> authenticated {
            effect { frame { nowhere } }
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:waive DUP001 reason="parallel test fixtures across 3 sibling \
    # test file(s) (7 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case/per-scenario coverage; extracting would obscure \
    # per-case intent"
    def test_record_audit_target_must_be_declared(self):
        text = """
        module m
        flow f1 : a -> b
        boundary b1 endorse f1 : foreign -> authenticated {
            record { audit to nowhere }
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:waive DUP001 reason="parallel test methods within \
    # test_boundary_phases.py (2 sites) sharing an arrange-act scaffold \
    # typical of exhaustive per-case coverage; extracting would obscure \
    # per-case intent"
    def test_refuse_frame_target_must_be_append_only(self):
        text = """
        module m
        node gw : authenticated
        node not_append_only : trusted
        flow f1 : gw -> gw
        boundary b1 endorse f1 : foreign -> authenticated {
            refuse { respond Public; frame { not_append_only } }
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.FrameViolation

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_refuse_respond_label_must_be_in_labels_lattice(self):
        text = """
        module m
        flow f1 : a -> b
        boundary b1 endorse f1 : foreign -> authenticated {
            refuse { respond NotALabel }
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownLevel


class TestOperationHappyPath:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_modifies_frames_become_conditioned_flows(self):
        text = """
        module m
        node LedgerDb : trusted
        operation Transfer on LedgerDb {
            modifies { Balance(from), Balance(to) } on Ok;
            modifies {} on Err;
            atomic via LedgerDb
        }
        """
        model = _elaborate(text).danger_ok
        ok_flows = [f for f in model.flows if f.id.startswith("Transfer__ok_")]
        assert len(ok_flows) == 2
        assert all(
            f.condition is not None and f.condition.outcome is Outcome.OK
            for f in ok_flows
        )
        assert {f.dst for f in ok_flows} == {"Balance", "Balance"}
        err_flows = [f for f in model.flows if f.id.startswith("Transfer__err_")]
        assert err_flows == []

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_coordinator_node_satisfies_strong_guarantee(self):
        text = """
        module m
        node StoreA : trusted
        node Coord : trusted { attr coordinator; }
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via Coord
        }
        """
        model = _elaborate(text).danger_ok
        assert model.nodes  # elaborates without error


class TestOperationFailClosed:
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_cross_store_atomic_via_without_coordinator_is_refused(self):
        text = """
        module m
        node StoreA : trusted
        node StoreB : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via StoreB
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.CrossStoreAtomicity

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_nonempty_err_frame_is_allowed_without_coordinator(self):
        text = """
        module m
        node StoreA : trusted
        node StoreB : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies { Slot } on Err;
            atomic via StoreB
        }
        """
        result = _elaborate(text)
        assert result.is_ok

    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:waive DUP001 reason="parallel test fixtures across 3 sibling \
    # test file(s) (7 sites) sharing an arrange-act scaffold typical of \
    # exhaustive per-case/per-scenario coverage; extracting would obscure \
    # per-case intent"
    def test_atomic_via_must_be_declared(self):
        text = """
        module m
        node StoreA : trusted
        operation Reserve on StoreA {
            modifies {} on Ok;
            modifies {} on Err;
            atomic via NoSuchNode
        }
        """
        result = _elaborate(text)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference
