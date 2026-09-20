"""T-4675 (SF-07): overdue-assume review dates are gate failures.

Positive/negative controls for `_claims.py::_eval_assumed` wiring the
charter-3 promise (`_models.py::Claim.review`, `docs/strata/evidence.md`)
that an overdue `review` date is a gate finding, not a silent
`Verdict.ASSUMED` warning. Pins a fixed "today" throughout so these can
never pass merely because a real calendar date drifted -- 33 of frob's own
assumes share one review date (2026-10-15) and must stay green until then.
"""

from __future__ import annotations

import datetime as dt

from frob.strata import (
    BoundClaim,
    Claim,
    KernelModel,
    Metric,
    Node,
    Quantity,
    Verdict,
    evaluate_claims,
)

# A date safely before any real assume's review date in design/frob.strata
# (2026-10-15) or after it -- never derived from `dt.date.today()`.
_FIXED_TODAY = dt.date(2026, 9, 19)


def _node(nid: str, trust: str = "trusted") -> Node:
    """A minimal trusted node for fixtures."""
    return Node(id=nid, trust=trust)


def _assume(review: str) -> Claim:
    """A single boilerplate-shaped assume claim (SF-08) with the given
    ISO `review` date, owned by a fixed test owner."""
    return Claim(
        id="assume:test",
        assumed=True,
        owner="test-owner",
        review=review,
        body=BoundClaim(
            metric=Metric.LATENCY,
            target="ghost-flow",
            limit=Quantity(value=1, unit="s"),
        ),
    )


def _evaluate(review: str, today: dt.date = _FIXED_TODAY):
    """Evaluate one assume claim against a fixed `today` and return its
    lone `ClaimResult`."""
    model = KernelModel(nodes=(_node("api"),), claims=(_assume(review),))
    results = evaluate_claims(model, today=today).danger_ok
    assert len(results) == 1
    return results[0]


class TestOverdueAssumeIsAGateFinding:
    """Positive control (acceptance [0]): an assume whose review date is
    in the past yields a gate FINDING, not `Verdict.ASSUMED` with only a
    logged warning. Fails at HEAD c8f56ef10, where `_eval_assumed` always
    returns `Verdict.ASSUMED`."""

    # frob:tests \
    # tests/unit/strata/test_claims_overdue.py::TestOverdueAssumeIsAGateFinding.test_overdue_review_yields_refuted_finding  # noqa: E501
    def test_overdue_review_yields_refuted_finding(self) -> None:
        # review date is one day before the fixed "today" above.
        result = _evaluate(review="2026-09-18")
        assert result.verdict is Verdict.REFUTED
        assert "overdue" in result.detail
        assert "assume:test" in result.detail
        assert "test-owner" in result.detail
        assert "2026-09-18" in result.detail

    # frob:tests \
    # tests/unit/strata/test_claims_overdue.py::TestOverdueAssumeIsAGateFinding.test_overdue_review_logs_warning_with_owner_and_date  # noqa: E501
    def test_overdue_review_logs_warning_with_owner_and_date(self, caplog) -> None:
        with caplog.at_level("WARNING"):
            _evaluate(review="2026-01-01")
        assert "assume:test" in caplog.text
        assert "overdue" in caplog.text
        assert "test-owner" in caplog.text


class TestFutureAssumeStaysAssumed:
    """Negative control (acceptance [1]): a review date still in the
    future must NOT start failing -- this must not flip all 33 of frob's
    own assumes before 2026-10-15."""

    # frob:tests \
    # tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed.test_future_review_stays_assumed_no_finding  # noqa: E501
    def test_future_review_stays_assumed_no_finding(self) -> None:
        # 10 days after the fixed "today" above -- still in the future.
        result = _evaluate(review="2026-09-29")
        assert result.verdict is Verdict.ASSUMED
        assert "overdue" not in result.detail

    # frob:tests \
    # tests/unit/strata/test_claims_overdue.py::TestFutureAssumeStaysAssumed.test_the_real_shared_cliff_date_is_still_future_at_the_fixed_today  # noqa: E501
    def test_the_real_shared_cliff_date_is_still_future_at_the_fixed_today(
        self,
    ) -> None:
        # design/frob.strata's own shared review date (26 days out from the
        # audit date), pinned against the fixed `_FIXED_TODAY` above so this
        # can never pass merely because a real calendar date drifted.
        result = _evaluate(review="2026-10-15")
        assert result.verdict is Verdict.ASSUMED
