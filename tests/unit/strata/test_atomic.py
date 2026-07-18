"""Unit tests for strata atomic/saga contracts
(docs/strata/boundary.md#frames-and-failure-atomicity, T-0075).
"""

from __future__ import annotations

from typani.error_set import ErrorSet

from frob.strata import (
    elaborate,
    evaluate_atomic_contracts,
    evaluate_saga_contracts,
    generate_fault_injection_cases,
    parse_module,
)

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
        # frob:tests src/frob/strata/_atomic.py::generate_fault_injection_cases kind="unit"
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
        # frob:tests src/frob/strata/_atomic.py::generate_fault_injection_cases kind="unit"
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
        # frob:tests src/frob/strata/_atomic.py::generate_fault_injection_cases kind="unit"
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
