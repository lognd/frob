"""Unit tests for strata deploy contracts (docs/strata/surface.md#std-deploy, T-0083)."""

from __future__ import annotations

from frob.strata import (
    Boundary,
    BoundaryDirection,
    BoundClaim,
    CanaryStage,
    Claim,
    DeployContract,
    Flow,
    KernelModel,
    Metric,
    Node,
    Quantity,
    StrataError,
    evaluate_deploy_contracts,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    return Flow(id=fid, src=src, dst=dst, **kw)


def _seconds(value: float) -> Quantity:
    return Quantity(value=value, unit="s")


def _endorse_boundary(bid: str, flow_id: str, **kw) -> Boundary:
    return Boundary(
        id=bid,
        flow_id=flow_id,
        direction=BoundaryDirection.ENDORSE,
        from_level="foreign",
        to_level="trusted",
        **kw,
    )


class TestEvaluateDeployContractsNoContracts:
    def test_empty_report_when_no_node_declares_a_deploy_contract(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(_node("a"), _node("b")), flows=(_flow("f1", "a", "b"),)
        )
        result = evaluate_deploy_contracts(model)
        assert result.is_ok
        assert result.danger_ok.scenario_results == ()


class TestEndorsementChainValidation:
    def test_unknown_endorsement_boundary_fails_closed(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "svc",
                    deploy=DeployContract(
                        stages=(),
                        endorsement_chain=("no_such_boundary",),
                        rollback_budget=_seconds(60),
                    ),
                ),
            ),
        )
        result = evaluate_deploy_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.MissingEndorsement

    def test_non_endorse_boundary_fails_closed(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(_node("cdn"), _node("origin")),
            flows=(_flow("f1", "cdn", "origin"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.DECLASSIFY,
                    from_level="Pii",
                    to_level="Public",
                ),
            ),
        )
        model = model.model_copy(
            update={
                "nodes": (
                    *model.nodes,
                    _node(
                        "svc",
                        deploy=DeployContract(
                            stages=(),
                            endorsement_chain=("b1",),
                            rollback_budget=_seconds(60),
                        ),
                    ),
                )
            }
        )
        result = evaluate_deploy_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.IncompatibleEndorsement

    def test_endorse_boundary_in_chain_passes(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("build"),
                _node("registry"),
                _node(
                    "svc",
                    deploy=DeployContract(
                        stages=(),
                        endorsement_chain=("b1",),
                        rollback_budget=_seconds(60),
                    ),
                ),
            ),
            flows=(_flow("f1", "build", "registry"),),
            boundaries=(_endorse_boundary("b1", "f1"),),
        )
        result = evaluate_deploy_contracts(model)
        assert result.is_ok


class TestCanaryLevelValidation:
    def test_unknown_canary_level_fails_closed(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "svc",
                    trust="authenticated",
                    deploy=DeployContract(
                        stages=(CanaryStage(level="bogus", bake=_seconds(300)),),
                        endorsement_chain=(),
                        rollback_budget=_seconds(60),
                    ),
                ),
            ),
        )
        result = evaluate_deploy_contracts(model)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownLevel

    def test_known_canary_level_passes(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "svc",
                    trust="authenticated",
                    deploy=DeployContract(
                        stages=(CanaryStage(level="trusted", bake=_seconds(300)),),
                        endorsement_chain=(),
                        rollback_budget=_seconds(60),
                    ),
                ),
            ),
        )
        result = evaluate_deploy_contracts(model)
        assert result.is_ok


class TestAutoGeneratedScenarios:
    def test_canary_and_rollback_scenarios_re_check_every_declared_claim(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node("a"),
                _node(
                    "svc",
                    deploy=DeployContract(
                        stages=(CanaryStage(level="trusted", bake=_seconds(300)),),
                        endorsement_chain=(),
                        rollback_budget=_seconds(60),
                    ),
                ),
            ),
            flows=(_flow("f1", "a", "svc"),),
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
        result = evaluate_deploy_contracts(model)
        assert result.is_ok
        report = result.danger_ok
        by_id = {r.scenario_id: r for r in report.scenario_results}
        assert by_id.keys() == {"svc__canary_0_trusted", "svc__rollback"}
        (canary_claim,) = by_id["svc__canary_0_trusted"].results
        assert canary_claim.claim_id == "capacity_ok"
        (rollback_claim,) = by_id["svc__rollback"].results
        assert rollback_claim.claim_id == "capacity_ok"

    def test_multiple_stages_generate_one_scenario_each_in_order(self):
        # frob:tests src/frob/strata/_deploy.py::evaluate_deploy_contracts kind="unit"
        model = KernelModel(
            nodes=(
                _node(
                    "svc",
                    trust="foreign",
                    deploy=DeployContract(
                        stages=(
                            CanaryStage(level="authenticated", bake=_seconds(300)),
                            CanaryStage(level="trusted", bake=_seconds(600)),
                        ),
                        endorsement_chain=(),
                        rollback_budget=_seconds(60),
                    ),
                ),
            ),
        )
        result = evaluate_deploy_contracts(model)
        assert result.is_ok
        scenario_ids = {r.scenario_id for r in result.danger_ok.scenario_results}
        assert scenario_ids == {
            "svc__canary_0_authenticated",
            "svc__canary_1_trusted",
            "svc__rollback",
        }
