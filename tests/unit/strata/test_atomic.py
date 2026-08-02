"""Unit tests for strata atomic/saga contracts
(docs/strata/boundary.md#frames-and-failure-atomicity, T-0075).
"""

from __future__ import annotations

from typani.error_set import ErrorSet
from typani.result import Err

from frob.strata import (
    elaborate,
    evaluate_atomic_contracts,
    evaluate_saga_contracts,
    generate_fault_injection_cases,
    parse_module,
)
from frob.strata._atomic import _join_saga_idempotency
from frob.strata._errors import StrataError

_AT_LEAST_ONCE = "delivery=at_least_once"


def _elaborate(text: str):
    module = parse_module(text).danger_ok
    return module, elaborate(module).danger_ok


class ReserveError(ErrorSet):
    """Fault vocabulary for a fake `Reserve` operation, used only by these tests."""

    Timeout = "the reservation call timed out"
    Conflict = "the slot was already reserved"


class TestEvaluateSagaContractsNoSaga:
    def test_empty_diagnostics_when_no_coordinator_declared(self):
        # frob:tests src/frob/strata/_atomic.py::evaluate_saga_contracts kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Slot : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via StoreA
        }
        """
        module, model = _elaborate(text)
        result = evaluate_saga_contracts(module, model)
        assert result.is_ok
        assert result.danger_ok == ()


class TestEvaluateSagaContractsJoin:
    def test_flow_into_coordinator_marked_at_least_once_and_joined(self):
        # frob:tests src/frob/strata/_atomic.py::evaluate_saga_contracts kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Coord : trusted { attr coordinator; }
        node caller : trusted
        node Slot : trusted
        flow f1 : caller -> Coord
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via Coord
        }
        """
        module, model = _elaborate(text)
        result = evaluate_saga_contracts(module, model)
        assert result.is_ok
        (diagnostic,) = result.danger_ok
        assert "Coord" in diagnostic
        assert "idempotent" in diagnostic

    def test_flow_into_idempotent_coordinator_produces_no_diagnostic(self):
        # frob:tests src/frob/strata/_atomic.py::evaluate_saga_contracts kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Coord : trusted { attr coordinator; attr idempotent; }
        node caller : trusted
        node Slot : trusted
        flow f1 : caller -> Coord
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via Coord
        }
        """
        module, model = _elaborate(text)
        result = evaluate_saga_contracts(module, model)
        assert result.is_ok
        assert result.danger_ok == ()

    def test_already_at_least_once_flow_is_not_double_marked(self):
        # frob:tests src/frob/strata/_atomic.py::evaluate_saga_contracts kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Coord : trusted { attr coordinator; }
        node caller : trusted
        node Slot : trusted
        flow f1 : caller -> Coord { attr delivery=at_least_once; }
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via Coord
        }
        """
        module, model = _elaborate(text)
        joined_flow = next(f for f in model.flows if f.id == "f1")
        assert joined_flow.attrs == (_AT_LEAST_ONCE,)
        result = evaluate_saga_contracts(module, model)
        assert result.is_ok
        (diagnostic,) = result.danger_ok
        assert "Coord" in diagnostic


class TestGenerateFaultInjectionCases:
    def test_strong_guarantee_operation_generates_one_case_per_variant(self):
        # frob:tests src/frob/strata/_atomic.py::generate_fault_injection_cases \
        # kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Slot : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via StoreA
        }
        """
        module, _ = _elaborate(text)
        cases = generate_fault_injection_cases(module, {"Reserve": ReserveError})
        timeout_case, conflict_case = cases
        assert timeout_case.error_variant == "Timeout"
        assert timeout_case.operation_id == "Reserve"
        assert timeout_case.id == "Reserve__fault_Timeout"
        assert conflict_case.error_variant == "Conflict"
        assert conflict_case.operation_id == "Reserve"

    def test_nonempty_err_frame_operation_is_not_eligible(self):
        # frob:tests src/frob/strata/_atomic.py::generate_fault_injection_cases \
        # kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Slot : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies { Slot } on Err;
            atomic via StoreA
        }
        """
        module, _ = _elaborate(text)
        cases = generate_fault_injection_cases(module, {"Reserve": ReserveError})
        assert cases == ()

    def test_operation_missing_from_error_sets_generates_nothing(self):
        # frob:tests src/frob/strata/_atomic.py::generate_fault_injection_cases \
        # kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Slot : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via StoreA
        }
        """
        module, _ = _elaborate(text)
        cases = generate_fault_injection_cases(module, {})
        assert cases == ()


class TestJoinSagaIdempotencyNoCoordinators:
    def test_empty_coordinator_ids_returns_model_unchanged(self):
        # frob:tests src/frob/strata/_atomic.py::_join_saga_idempotency kind="unit"
        """Calling the private join directly with no coordinator ids must
        short-circuit and hand back the exact same model, never touching
        `flows` -- the guard `evaluate_saga_contracts` normally applies
        before ever reaching this helper (T-0075)."""
        text = """
        module m
        node StoreA : trusted
        node Slot : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via StoreA
        }
        """
        _, model = _elaborate(text)
        result = _join_saga_idempotency(model, frozenset())
        assert result is model


class TestEvaluateSagaContractsFactsError:
    def test_build_facts_error_is_propagated(self, monkeypatch):
        # frob:tests src/frob/strata/_atomic.py::evaluate_saga_contracts kind="unit"
        """When `build_facts` fails on the joined model, the error must
        propagate through as `Err`, never be swallowed or replaced with an
        empty diagnostics tuple."""
        import frob.strata._atomic as atomic_mod

        text = """
        module m
        node StoreA : trusted
        node Coord : trusted { attr coordinator; }
        node caller : trusted
        node Slot : trusted
        flow f1 : caller -> Coord
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via Coord
        }
        """
        module, model = _elaborate(text)
        monkeypatch.setattr(
            atomic_mod, "build_facts", lambda _model: Err(StrataError.MalformedLattice)
        )
        result = evaluate_saga_contracts(module, model)
        assert result.is_err
        assert result.danger_err is StrataError.MalformedLattice


class TestEvaluateAtomicContractsSagaError:
    def test_saga_error_short_circuits_before_fault_injection(self, monkeypatch):
        # frob:tests src/frob/strata/_atomic.py::evaluate_atomic_contracts kind="unit"
        """A failing `evaluate_saga_contracts` must abort `evaluate_atomic_
        contracts` immediately -- `generate_fault_injection_cases` must
        never be reached."""
        import frob.strata._atomic as atomic_mod

        text = """
        module m
        node StoreA : trusted
        node Slot : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via StoreA
        }
        """
        module, model = _elaborate(text)
        monkeypatch.setattr(
            atomic_mod,
            "evaluate_saga_contracts",
            lambda _module, _model: Err(StrataError.MalformedLattice),
        )
        called = []
        monkeypatch.setattr(
            atomic_mod,
            "generate_fault_injection_cases",
            lambda *a, **k: called.append(1) or (),
        )
        result = evaluate_atomic_contracts(
            module, model, error_sets={"Reserve": ReserveError}
        )
        assert result.is_err
        assert result.danger_err is StrataError.MalformedLattice
        assert called == []


class TestEvaluateAtomicContracts:
    def test_joins_saga_diagnostics_and_fault_injection_cases(self):
        # frob:tests src/frob/strata/_atomic.py::evaluate_atomic_contracts kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Coord : trusted { attr coordinator; }
        node caller : trusted
        node Slot : trusted
        flow f1 : caller -> Coord
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via Coord
        }
        """
        module, model = _elaborate(text)
        result = evaluate_atomic_contracts(
            module, model, error_sets={"Reserve": ReserveError}
        )
        assert result.is_ok
        report = result.danger_ok
        assert len(report.saga_diagnostics) == 1
        assert len(report.fault_injection_cases) == 2

    def test_defaults_to_no_fault_injection_cases_without_error_sets(self):
        # frob:tests src/frob/strata/_atomic.py::evaluate_atomic_contracts kind="unit"
        text = """
        module m
        node StoreA : trusted
        node Slot : trusted
        operation Reserve on StoreA {
            modifies { Slot } on Ok;
            modifies {} on Err;
            atomic via StoreA
        }
        """
        module, model = _elaborate(text)
        result = evaluate_atomic_contracts(module, model)
        assert result.is_ok
        assert result.danger_ok.fault_injection_cases == ()
        assert result.danger_ok.saga_diagnostics == ()
