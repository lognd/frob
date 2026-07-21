"""Unit tests for strata claim evaluation (docs/strata/kernel.md)."""

from __future__ import annotations

import datetime as dt

from frob.strata import (
    Boundary,
    BoundaryDirection,
    BoundClaim,
    Capacity,
    Claim,
    Flow,
    KernelModel,
    Metric,
    Node,
    NoFlow,
    Quantifier,
    Quantity,
    Reach,
    StrataError,
    Verdict,
    evaluate_claims,
)


def _node(nid: str, trust: str = "trusted", **kw) -> Node:
    return Node(id=nid, trust=trust, **kw)


def _flow(fid: str, src: str, dst: str, **kw) -> Flow:
    return Flow(id=fid, src=src, dst=dst, **kw)


def _one(model: KernelModel):
    results = evaluate_claims(model, today=dt.date(2026, 7, 17)).danger_ok
    assert len(results) == 1
    return results[0]


class TestNoFlow:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_refuted_with_witness_path_when_no_boundary_intervenes(self):
        model = KernelModel(
            nodes=(_node("evil", trust="foreign"), _node("api"), _node("db")),
            flows=(_flow("f1", "evil", "api"), _flow("f2", "api", "db")),
            claims=(Claim(id="c1", body=NoFlow(src="foreign", dst="db")),),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert result.quantifier is Quantifier.FORALL
        assert result.counterexample == ("evil", "f1", "api", "f2", "db")

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_proved_forall_when_an_endorsement_boundary_cuts_the_path(self):
        model = KernelModel(
            nodes=(_node("evil", trust="foreign"), _node("api"), _node("db")),
            flows=(_flow("f1", "evil", "api"), _flow("f2", "api", "db")),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="authenticated",
                ),
            ),
            claims=(Claim(id="c1", body=NoFlow(src="foreign", dst="db")),),
        )
        result = _one(model)
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.FORALL

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_unknown_endpoint_fails_closed(self):
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(Claim(id="c1", body=NoFlow(src="ghost", dst="api")),),
        )
        outcome = evaluate_claims(model)
        assert outcome.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_real_leak_through_a_utility_hub_still_refutes(self):
        """T-0496 (docs/audits/strata.md G5) litmus, straight from the
        ticket's own repro: `log_hub{utility}` from `secret_store` to
        `logger`, then a REAL leak edge `logger -> foreign_sink` -- before
        this fix, `noflow(secret_store, foreign_sink)` PROVED despite the
        two-hop leak (the `utility` marker made `logger` unreachable-past
        even though `logger` had its own transitive outgoing edge). Must
        now REFUTE with the full two-hop witness."""
        model = KernelModel(
            nodes=(_node("secret_store"), _node("logger"), _node("foreign_sink")),
            flows=(
                _flow("log_hub", "secret_store", "logger", attrs=("utility",)),
                _flow("leak", "logger", "foreign_sink"),
            ),
            claims=(
                Claim(id="c1", body=NoFlow(src="secret_store", dst="foreign_sink")),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert result.counterexample == (
            "secret_store",
            "log_hub",
            "logger",
            "leak",
            "foreign_sink",
        )

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_utility_hub_with_no_further_edges_still_discharges(self):
        """The T-0226 case `utility` originally existed for is unaffected:
        an innocuous hub with NOTHING downstream still lets `noflow` prove
        clean -- this fix only stops `utility` from HIDING a real further
        edge, it does not reintroduce a spurious refutation for a hub that
        genuinely goes nowhere else."""
        model = KernelModel(
            nodes=(_node("secret_store"), _node("logger"), _node("unrelated")),
            flows=(_flow("log_hub", "secret_store", "logger", attrs=("utility",)),),
            claims=(Claim(id="c1", body=NoFlow(src="secret_store", dst="unrelated")),),
        )
        result = _one(model)
        assert result.verdict is Verdict.PROVED


class TestReach:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_proved_exists_with_witness_even_through_boundaries(self):
        model = KernelModel(
            nodes=(_node("gw"), _node("audit")),
            flows=(_flow("f1", "gw", "audit"),),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="authenticated",
                ),
            ),
            claims=(Claim(id="c1", body=Reach(src="gw", dst="audit")),),
        )
        result = _one(model)
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.EXISTS
        assert result.counterexample == ("gw", "f1", "audit")

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_refutation_of_exists_is_a_forall(self):
        model = KernelModel(
            nodes=(_node("gw"), _node("audit")),
            claims=(Claim(id="c1", body=Reach(src="gw", dst="audit")),),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert result.quantifier is Quantifier.FORALL


class TestBounds:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_age_bound_refuted_with_stalest_path_and_number(self):
        model = KernelModel(
            nodes=(_node("truth"), _node("replica"), _node("view")),
            flows=(
                _flow("f1", "truth", "replica", age=Quantity(value=5, unit="min")),
                _flow("f2", "replica", "view", age=Quantity(value=30, unit="s")),
            ),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.AGE,
                        target="view",
                        limit=Quantity(value=60, unit="s"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert "330.0s > 60.0s" in result.detail
        assert result.counterexample[0] == "truth"

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_age_bound_proved_when_within_limit(self):
        model = KernelModel(
            nodes=(_node("truth"), _node("view")),
            flows=(_flow("f1", "truth", "view", age=Quantity(value=10, unit="s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.AGE,
                        target="view",
                        limit=Quantity(value=1, unit="min"),
                    ),
                ),
            ),
        )
        assert _one(model).verdict is Verdict.PROVED

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_age_limit_of_wrong_dimension_fails_closed(self):
        model = KernelModel(
            nodes=(_node("view"),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.AGE,
                        target="view",
                        limit=Quantity(value=1, unit="KiB"),
                    ),
                ),
            ),
        )
        assert evaluate_claims(model).danger_err is StrataError.UnitMismatch

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_utilization_refuted_without_declared_capacity(self):
        model = KernelModel(
            nodes=(_node("src"), _node("api")),
            flows=(_flow("f1", "src", "api", rate=Quantity(value=10, unit="req/s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="api",
                        limit=Quantity(value=70, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.REFUTED
        assert "declares no capacity" in result.detail

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_utilization_proved_against_replica_ceiling(self):
        model = KernelModel(
            nodes=(
                _node("src"),
                _node(
                    "api",
                    capacity=Capacity(
                        service_rate=Quantity(value=100, unit="req/s"),
                        replicas_min=2,
                        replicas_max=4,
                    ),
                ),
            ),
            flows=(_flow("f1", "src", "api", rate=Quantity(value=200, unit="req/s")),),
            claims=(
                Claim(
                    id="c1",
                    body=BoundClaim(
                        metric=Metric.UTILIZATION,
                        target="api",
                        limit=Quantity(value=70, unit="%"),
                    ),
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.PROVED
        assert "50.0%" in result.detail


class TestAssumes:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_assume_closes_as_assumed_with_owner_and_review(self):
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(
                Claim(
                    id="a1",
                    body=NoFlow(src="foreign", dst="api"),
                    assumed=True,
                    owner="logan",
                    review="2026-10-01",
                ),
            ),
        )
        result = _one(model)
        assert result.verdict is Verdict.ASSUMED
        assert "logan" in result.detail
        assert "review by 2026-10-01" in result.detail

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_overdue_assume_is_flagged_in_detail(self):
        model = KernelModel(
            nodes=(_node("api"),),
            claims=(
                Claim(
                    id="a1",
                    body=NoFlow(src="foreign", dst="api"),
                    assumed=True,
                    owner="logan",
                    review="2026-01-01",
                ),
            ),
        )
        assert "overdue since 2026-01-01" in _one(model).detail
