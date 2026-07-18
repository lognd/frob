"""Unit tests for strata breach scenarios: blast radius + recovery-path
independence (docs/strata/kernel.md#scenario, T-0076)."""

from __future__ import annotations

from frob.strata import (
    BreachContract,
    Flow,
    Independent,
    KernelModel,
    Node,
    Quantity,
    StrataError,
    Verdict,
    evaluate_breach_contracts,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    return Flow(id=fid, src=src, dst=dst, **kw)


def _seconds(value: float) -> Quantity:
    return Quantity(value=value, unit="s")


class TestEvaluateBreachContractsNoContracts:
    def test_empty_report_when_no_node_declares_a_breach_contract(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(_node("a"), _node("b")),
            flows=(_flow("f1", "a", "b"),),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        report = result.danger_ok
        assert report.scenario_results == ()
        assert report.blast_radii == ()


class TestRecoveryViaValidation:
    def test_unknown_recovers_via_target_fails_closed(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "gateway",
                    breach=BreachContract(
                        detect=_seconds(60),
                        revoke=_seconds(120),
                        recovers_via="no_such_node",
                    ),
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    def test_declared_recovers_via_target_passes(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("recovery_svc"),
                _node(
                    "gateway",
                    breach=BreachContract(
                        detect=_seconds(60),
                        revoke=_seconds(120),
                        recovers_via="recovery_svc",
                    ),
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok


class TestContainmentBounds:
    def test_detection_sla_exceeding_revocation_bound_fails_closed(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "gateway",
                    breach=BreachContract(detect=_seconds(200), revoke=_seconds(60)),
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.IncompatibleContainmentBound

    def test_credential_age_outliving_revocation_fails_closed(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "gateway",
                    breach=BreachContract(
                        detect=_seconds(30),
                        revoke=_seconds(60),
                        credential_age=_seconds(600),
                    ),
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.IncompatibleContainmentBound

    def test_bounds_within_revocation_window_pass(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "gateway",
                    breach=BreachContract(
                        detect=_seconds(30),
                        revoke=_seconds(60),
                        credential_age=_seconds(45),
                    ),
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok


class TestBlastRadius:
    def test_blast_radius_is_the_reach_closure_from_the_breached_node(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "gateway",
                    breach=BreachContract(detect=_seconds(30), revoke=_seconds(60)),
                ),
                _node("store"),
                _node("unreached"),
            ),
            flows=(_flow("f1", "gateway", "store"),),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        (radius,) = result.danger_ok.blast_radii
        assert radius.node_id == "gateway"
        assert radius.reached == ("store",)

    def test_blast_radius_crosses_declared_boundaries(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        from frob.strata import Boundary, BoundaryDirection

        model = KernelModel(
            nodes=(
                _node(
                    "gateway",
                    trust="foreign",
                    breach=BreachContract(detect=_seconds(30), revoke=_seconds(60)),
                ),
                _node("api"),
            ),
            flows=(_flow("f1", "gateway", "api"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        (radius,) = result.danger_ok.blast_radii
        assert "api" in radius.reached

    def test_two_breachable_nodes_report_radii_in_sorted_id_order(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "z_node", breach=BreachContract(detect=_seconds(1), revoke=_seconds(2))
                ),
                _node(
                    "a_node", breach=BreachContract(detect=_seconds(1), revoke=_seconds(2))
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        ids = [r.node_id for r in result.danger_ok.blast_radii]
        assert ids == ["a_node", "z_node"]


class TestAutoGeneratedBreachScenario:
    def test_breach_scenario_re_checks_every_declared_claim(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        from frob.strata import BoundClaim, Claim, Metric

        model = KernelModel(
            nodes=(
                _node("a"),
                _node(
                    "gateway",
                    breach=BreachContract(detect=_seconds(30), revoke=_seconds(60)),
                ),
            ),
            flows=(_flow("f1", "a", "gateway"),),
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
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        (scenario,) = result.danger_ok.scenario_results
        assert scenario.scenario_id == "gateway__breach"
        (claim_result,) = scenario.results
        assert claim_result.claim_id == "capacity_ok"

    def test_two_breachable_nodes_generate_scenarios_in_sorted_id_order(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "z_node", breach=BreachContract(detect=_seconds(1), revoke=_seconds(2))
                ),
                _node(
                    "a_node", breach=BreachContract(detect=_seconds(1), revoke=_seconds(2))
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        ids = [s.scenario_id for s in result.danger_ok.scenario_results]
        assert ids == ["a_node__breach", "z_node__breach"]


class TestRecoveryPathIndependence:
    def test_recovery_path_disjoint_from_blast_radius_is_proved(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("recovery_svc"),
                _node(
                    "gateway",
                    breach=BreachContract(
                        detect=_seconds(30),
                        revoke=_seconds(60),
                        recovers_via="recovery_svc",
                    ),
                ),
            ),
            flows=(_flow("f1", "recovery_svc", "gateway"),),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        (scenario,) = result.danger_ok.scenario_results
        (claim_result,) = scenario.results
        assert claim_result.claim_id == "gateway__recovery_independent"
        assert claim_result.verdict is Verdict.PROVED

    def test_recovery_path_through_blast_radius_is_refuted(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("recovery_svc"),
                _node(
                    "gateway",
                    breach=BreachContract(
                        detect=_seconds(30),
                        revoke=_seconds(60),
                        recovers_via="recovery_svc",
                    ),
                ),
                _node("shared_store"),
            ),
            flows=(
                # recovery_svc's path to gateway routes through shared_store,
                # which the breached gateway can also reach -- not independent.
                _flow("f1", "recovery_svc", "shared_store"),
                _flow("f2", "shared_store", "gateway"),
                _flow("f3", "gateway", "shared_store"),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        (scenario,) = result.danger_ok.scenario_results
        (claim_result,) = scenario.results
        assert claim_result.claim_id == "gateway__recovery_independent"
        assert claim_result.verdict is Verdict.REFUTED
        assert "shared_store" in claim_result.counterexample

    def test_no_recovers_via_generates_no_independence_claim(self):
        # frob:tests src/frob/strata/_breach.py::evaluate_breach_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "gateway",
                    breach=BreachContract(detect=_seconds(30), revoke=_seconds(60)),
                ),
            ),
        )
        result = evaluate_breach_contracts(model)
        assert result.is_ok
        (scenario,) = result.danger_ok.scenario_results
        assert scenario.results == ()


class TestIndependentClaimDirectly:
    def test_independent_claim_proved_when_paths_disjoint(self):
        # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
        from frob.strata import Claim, evaluate_claims

        model = KernelModel(
            nodes=(_node("recovery"), _node("compromised"), _node("other")),
            flows=(_flow("f1", "recovery", "other"),),
            claims=(
                Claim(
                    id="rec_independent",
                    body=Independent(
                        src="recovery", dst="other", avoid="compromised"
                    ),
                ),
            ),
        )
        result = evaluate_claims(model)
        assert result.is_ok
        (claim_result,) = result.danger_ok
        assert claim_result.verdict is Verdict.PROVED

    def test_independent_claim_refuted_when_no_path_exists(self):
        # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
        from frob.strata import Claim, evaluate_claims

        model = KernelModel(
            nodes=(_node("recovery"), _node("other"), _node("compromised")),
            claims=(
                Claim(
                    id="rec_independent",
                    body=Independent(
                        src="recovery", dst="other", avoid="compromised"
                    ),
                ),
            ),
        )
        result = evaluate_claims(model)
        assert result.is_ok
        (claim_result,) = result.danger_ok
        assert claim_result.verdict is Verdict.PROVED

    def test_independent_claim_unknown_reference_fails_closed(self):
        # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
        from frob.strata import Claim, evaluate_claims

        model = KernelModel(
            nodes=(_node("recovery"), _node("other")),
            claims=(
                Claim(
                    id="rec_independent",
                    body=Independent(
                        src="recovery", dst="other", avoid="no_such_node"
                    ),
                ),
            ),
        )
        result = evaluate_claims(model)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference
