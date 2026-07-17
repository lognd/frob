"""Payments litmus model as hand-written kernel facts (docs/strata/roadmap.md).

The phase-0 exit criterion (T-0058): a Stripe-shaped payments system whose
golden findings each correspond to a real production bug class. The same
model moves to surface syntax in design/litmus/payments.strata at phase 1
(T-0063) and must keep firing these exact findings forever after.
"""

from __future__ import annotations

import datetime as dt

from frob.strata import (
    Boundary,
    BoundaryDirection,
    BoundClaim,
    Claim,
    ClaimResult,
    Flow,
    KernelModel,
    Metric,
    Node,
    NoFlow,
    Quantifier,
    Quantity,
    Reach,
    Verdict,
    build_facts,
    evaluate_claims,
)

_TODAY = dt.date(2026, 7, 17)


def _ingress_boundary() -> Boundary:
    return Boundary(
        id="b_ingress",
        flow_id="f_ingress",
        direction=BoundaryDirection.ENDORSE,
        from_level="foreign",
        to_level="authenticated",
        predicate="jwt_verified",
    )


def _payments_model(*, hardened: bool) -> KernelModel:
    """The litmus system; `hardened=True` applies every golden finding's remedy."""
    api_attrs = ("idempotent",) if hardened else ()
    refund_reads = (
        Flow(id="f_refund_read", src="ledger", dst="refund")  # leader read
        if hardened
        else Flow(id="f_refund_read", src="dashboard", dst="refund")  # stale read
    )
    boundaries = [_ingress_boundary()]
    if hardened:
        boundaries.append(
            Boundary(
                id="b_stripe_resp",
                flow_id="f_stripe_resp",
                direction=BoundaryDirection.ENDORSE,
                from_level="authenticated",
                to_level="trusted",
                predicate="schema_validated",
            )
        )
        # Found by the checker itself: endorsing the response path alone
        # still leaves stripe -> webhookq -> api -> ledger unendorsed.
        boundaries.append(
            Boundary(
                id="b_webhook",
                flow_id="f_wq_api",
                direction=BoundaryDirection.ENDORSE,
                from_level="authenticated",
                to_level="trusted",
                predicate="webhook_signature_verified",
            )
        )
    return KernelModel(
        nodes=(
            Node(id="browser", trust="foreign", clearance="Public"),
            Node(id="stripe", trust="authenticated", clearance="Internal"),
            Node(id="gateway", trust="trusted", clearance="Pii"),
            Node(id="api", trust="trusted", clearance="Pii", attrs=api_attrs),
            Node(id="ledger", trust="trusted", clearance="Secret"),
            Node(id="replica", trust="trusted", clearance="Secret"),
            Node(id="dashboard", trust="trusted", clearance="Internal"),
            Node(id="refund", trust="trusted", clearance="Pii"),
            Node(
                id="webhookq",
                trust="trusted",
                clearance="Internal",
                attrs=("idempotent",) if hardened else (),  # dedup by event id
            ),
            Node(id="audit", trust="trusted", clearance="Secret"),
        ),
        flows=(
            Flow(id="f_ingress", src="browser", dst="gateway", label="Pii"),
            Flow(id="f_gw_api", src="gateway", dst="api", label="Pii"),
            Flow(id="f_api_ledger", src="api", dst="ledger", label="Pii"),
            Flow(id="f_stripe_resp", src="stripe", dst="api", label="Internal"),
            Flow(
                id="f_repl",
                src="ledger",
                dst="replica",
                label="Internal",
                age=Quantity(value=5, unit="min"),
            ),
            Flow(
                id="f_dash",
                src="replica",
                dst="dashboard",
                label="Internal",
                age=Quantity(value=30, unit="s"),
            ),
            refund_reads,
            Flow(
                id="f_webhook",
                src="stripe",
                dst="webhookq",
                label="Internal",
                attrs=("delivery=at_least_once",),
            ),
            Flow(
                id="f_wq_api",
                src="webhookq",
                dst="api",
                label="Internal",
                attrs=("delivery=at_least_once",),
            ),
            Flow(id="f_gw_audit", src="gateway", dst="audit", label="Internal"),
        ),
        boundaries=tuple(boundaries),
        claims=(
            Claim(id="c_no_browser_ledger", body=NoFlow(src="browser", dst="ledger")),
            Claim(id="c_no_stripe_ledger", body=NoFlow(src="stripe", dst="ledger")),
            Claim(
                id="c_fresh_refund",
                body=BoundClaim(
                    metric=Metric.AGE,
                    target="refund",
                    limit=Quantity(value=60, unit="s"),
                ),
            ),
            Claim(id="c_audit_path", body=Reach(src="gateway", dst="audit")),
            Claim(
                id="a_disk_encryption",
                body=NoFlow(src="foreign", dst="ledger"),
                assumed=True,
                owner="logan",
                review="2026-10-01",
            ),
        ),
    )


def _results(model: KernelModel) -> dict[str, ClaimResult]:
    evaluated = evaluate_claims(model, today=_TODAY).danger_ok
    return {r.claim_id: r for r in evaluated}


class TestGoldenFindings:
    """The naive model must fire every golden finding, with witnesses."""

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_golden_1_third_party_response_reaches_ledger_unendorsed(self):
        result = _results(_payments_model(hardened=False))["c_no_stripe_ledger"]
        assert result.verdict is Verdict.REFUTED
        assert result.counterexample == (
            "stripe",
            "f_stripe_resp",
            "api",
            "f_api_ledger",
            "ledger",
        )

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_golden_2_refund_decision_reads_a_stale_replica(self):
        result = _results(_payments_model(hardened=False))["c_fresh_refund"]
        assert result.verdict is Verdict.REFUTED
        assert "330.0s > 60.0s" in result.detail
        assert result.counterexample == (
            "ledger",
            "f_repl",
            "replica",
            "f_dash",
            "dashboard",
            "f_refund_read",
            "refund",
        )

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_golden_3_at_least_once_webhook_into_non_idempotent_consumer(self):
        facts = build_facts(_payments_model(hardened=False)).danger_ok
        assert any(
            "f_wq_api" in d and "not declared idempotent" in d
            for d in facts.diagnostics
        )

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_endorsed_browser_ingress_is_proved_even_in_the_naive_model(self):
        result = _results(_payments_model(hardened=False))["c_no_browser_ledger"]
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.FORALL

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_audit_reach_carries_an_exists_witness(self):
        result = _results(_payments_model(hardened=False))["c_audit_path"]
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.EXISTS
        assert result.counterexample == ("gateway", "f_gw_audit", "audit")

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_the_assume_is_ledgered_not_proved(self):
        result = _results(_payments_model(hardened=False))["a_disk_encryption"]
        assert result.verdict is Verdict.ASSUMED
        assert "logan" in result.detail


class TestHardenedModel:
    """Applying each remedy flips its finding; nothing else regresses."""

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_every_assert_holds_after_the_remedies(self):
        results = _results(_payments_model(hardened=True))
        assert results["c_no_stripe_ledger"].verdict is Verdict.PROVED
        assert results["c_fresh_refund"].verdict is Verdict.PROVED
        assert results["c_no_browser_ledger"].verdict is Verdict.PROVED
        assert results["c_audit_path"].verdict is Verdict.PROVED

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_idempotent_consumer_clears_the_delivery_diagnostic(self):
        facts = build_facts(_payments_model(hardened=True)).danger_ok
        assert facts.diagnostics == ()
