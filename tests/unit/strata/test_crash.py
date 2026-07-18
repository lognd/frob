"""Unit tests for strata crash contracts
(docs/strata/boundary.md#crash-contracts-and-error-totality-adjacent-claims, T-0074).
"""

from __future__ import annotations

from frob.strata import (
    BoundClaim,
    Claim,
    CrashContract,
    Flow,
    KernelModel,
    Metric,
    Node,
    Quantity,
    StrataError,
    Verdict,
    evaluate_crash_contracts,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    return Flow(id=fid, src=src, dst=dst, **kw)


def _seconds(value: float) -> Quantity:
    return Quantity(value=value, unit="s")


class TestEvaluateCrashContractsNoContracts:
    def test_empty_report_when_no_node_declares_a_crash_contract(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok
        report = result.danger_ok
        assert report.scenario_results == ()
        assert report.diagnostics == ()


class TestNoHangCheck:
    def test_missing_timeout_into_crashable_node_fails_closed(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("caller"),
                _node("worker", crash=CrashContract(restart=_seconds(30))),
            ),
            flows=(_flow("f1", "caller", "worker"),),  # no timeout attr
        )
        result = evaluate_crash_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.MissingTimeout

    def test_timeout_shorter_than_restart_bound_fails_closed(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("caller"),
                _node("worker", crash=CrashContract(restart=_seconds(30))),
            ),
            flows=(_flow("f1", "caller", "worker", timeout=_seconds(5)),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.IncompatibleTimeout

    def test_timeout_covering_restart_plus_retry_bound_passes(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("caller"),
                _node(
                    "worker",
                    attrs=("idempotent",),
                    crash=CrashContract(restart=_seconds(30), retry=_seconds(10)),
                ),
            ),
            flows=(_flow("f1", "caller", "worker", timeout=_seconds(40)),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok

    def test_async_flow_is_exempt_from_the_no_hang_check(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("caller"),
                _node("worker", crash=CrashContract(restart=_seconds(30))),
            ),
            flows=(_flow("f1", "caller", "worker", attrs=("async",)),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok


class TestRecoverySourceValidation:
    def test_unknown_recovers_from_target_fails_closed(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "worker",
                    crash=CrashContract(
                        restart=_seconds(30), recovers_from="no_such_store"
                    ),
                ),
            ),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    def test_declared_recovers_from_target_passes(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("store"),
                _node(
                    "worker",
                    crash=CrashContract(restart=_seconds(30), recovers_from="store"),
                ),
            ),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok


class TestCrashRetryIdempotencyJoin:
    def test_retry_into_non_idempotent_node_is_a_diagnostic(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("caller"),
                _node(
                    "worker",  # no "idempotent" attr
                    crash=CrashContract(restart=_seconds(30), retry=_seconds(10)),
                ),
            ),
            flows=(_flow("f1", "caller", "worker", timeout=_seconds(40)),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok
        report = result.danger_ok
        assert any("at-least-once" in d and "worker" in d for d in report.diagnostics)

    def test_retry_into_idempotent_node_has_no_diagnostic(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("caller"),
                _node(
                    "worker",
                    attrs=("idempotent",),
                    crash=CrashContract(restart=_seconds(30), retry=_seconds(10)),
                ),
            ),
            flows=(_flow("f1", "caller", "worker", timeout=_seconds(40)),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok
        assert result.danger_ok.diagnostics == ()

    def test_restart_only_contract_without_retry_does_not_demand_idempotency(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("caller"),
                _node("worker", crash=CrashContract(restart=_seconds(30))),
            ),
            flows=(_flow("f1", "caller", "worker", timeout=_seconds(30)),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok
        assert result.danger_ok.diagnostics == ()


class TestAutoGeneratedCrashScenario:
    def test_crash_scenario_re_checks_every_declared_claim(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("a"),
                _node("worker", crash=CrashContract(restart=_seconds(30))),
            ),
            flows=(_flow("f1", "a", "worker", timeout=_seconds(30)),),
            claims=(
                Claim(
                    id="capacity_ok",
                    body=BoundClaim(
                        metric=Metric.RATE,
                        target="a",
                        limit=Quantity(value=100, unit="req/s"),
                    ),
                ),
            ),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok
        report = result.danger_ok
        (scenario,) = report.scenario_results
        assert scenario.scenario_id == "worker__crash"
        (claim_result,) = scenario.results
        assert claim_result.claim_id == "capacity_ok"

    def test_two_crashable_nodes_generate_scenarios_in_sorted_id_order(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("a"),
                _node("z_worker", crash=CrashContract(restart=_seconds(30))),
                _node("a_worker", crash=CrashContract(restart=_seconds(30))),
            ),
            flows=(
                _flow("f1", "a", "z_worker", timeout=_seconds(30)),
                _flow("f2", "a", "a_worker", timeout=_seconds(30)),
            ),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok
        ids = [s.scenario_id for s in result.danger_ok.scenario_results]
        assert ids == ["a_worker__crash", "z_worker__crash"]

    def test_crash_scenario_removing_the_node_can_refute_a_reach_claim(self):
        # frob:tests src/frob/strata/_crash.py::evaluate_crash_contracts kind="unit"
        from frob.strata import Reach

        model = KernelModel(
            nodes=(
                _node("audit_src"),
                _node("worker", crash=CrashContract(restart=_seconds(30))),
                _node("sink"),
            ),
            flows=(
                _flow("f1", "audit_src", "worker", timeout=_seconds(30)),
                _flow("f2", "worker", "sink"),
            ),
            claims=(Claim(id="must_reach", body=Reach(src="audit_src", dst="sink")),),
        )
        result = evaluate_crash_contracts(model)
        assert result.is_ok
        (scenario,) = result.danger_ok.scenario_results
        # worker (and its flows) are removed under its own crash scenario, so
        # audit_src can no longer reach sink through it.
        assert scenario.results[0].verdict is Verdict.REFUTED
