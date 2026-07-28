"""Surface-syntax payments litmus goldens (docs/strata/roadmap.md, T-0063).

Phase-1 exit criterion: `design/litmus/payments.strata` and
`design/litmus/payments_hardened.strata` must reproduce, end to end through
`parse_module -> elaborate -> evaluate_claims`, the exact same golden
findings as the phase-0 hand-written kernel-facts model in
`test_litmus_payments.py`. These goldens are permanent CI fixtures
(docs/strata/roadmap.md#the-litmus-program): a language change that stops
one of these findings from firing is a regression, not a feature.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from frob.strata import (
    ClaimResult,
    KernelModel,
    Quantifier,
    Verdict,
    build_facts,
    elaborate,
    evaluate_claims,
    parse_module,
    render_report,
)

_TODAY = dt.date(2026, 7, 17)


def _repo_root() -> Path:
    """Walk up from this file until a directory containing `frob.toml` is found."""
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        if (candidate / "frob.toml").is_file():
            return candidate
    raise RuntimeError(
        "could not locate repo root (no frob.toml found above test file)"
    )


_LITMUS_DIR = _repo_root() / "design" / "litmus"


def _load_model(filename: str) -> KernelModel:
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


def _results(model: KernelModel) -> dict[str, ClaimResult]:
    evaluated = evaluate_claims(model, today=_TODAY).danger_ok
    return {r.claim_id: r for r in evaluated}


# frob:doc docs/guides/extending/litmus-fixtures.md#litmus-fixture-mappings
class TestNaiveSurfaceGoldens:
    """payments.strata must reproduce every phase-0 kernel-facts golden finding."""

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_golden_1_third_party_response_reaches_ledger_unendorsed(self):
        result = _results(_load_model("payments.strata"))["c_no_stripe_ledger"]
        assert result.verdict is Verdict.REFUTED
        assert result.counterexample == (
            "stripe",
            "f_stripe_resp",
            "api",
            "f_api_ledger",
            "ledger",
        )

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_golden_2_refund_decision_reads_a_stale_replica(self):
        result = _results(_load_model("payments.strata"))["c_fresh_refund"]
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

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_golden_3_at_least_once_webhook_into_non_idempotent_consumer(self):
        facts = build_facts(_load_model("payments.strata")).danger_ok
        assert any(
            "f_wq_api" in d and "not declared idempotent" in d
            for d in facts.diagnostics
        )

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_endorsed_browser_ingress_is_proved_even_in_the_naive_model(self):
        result = _results(_load_model("payments.strata"))["c_no_browser_ledger"]
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.FORALL

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_audit_reach_carries_an_exists_witness(self):
        result = _results(_load_model("payments.strata"))["c_audit_path"]
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.EXISTS
        assert result.counterexample == ("gateway", "f_gw_audit", "audit")

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_the_assume_is_ledgered_not_proved(self):
        result = _results(_load_model("payments.strata"))["a_disk_encryption"]
        assert result.verdict is Verdict.ASSUMED
        assert "logan" in result.detail

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_render_report_shows_refuted_before_proved_with_the_witness_path(self):
        results = evaluate_claims(
            _load_model("payments.strata"), today=_TODAY
        ).danger_ok
        report = render_report(results)
        assert report.index("REFUTED") < report.index("PROVED")
        assert (
            "  path: stripe -> f_stripe_resp -> api -> f_api_ledger -> ledger" in report
        )


class TestHardenedSurfaceGoldens:
    """payments_hardened.strata must flip every naive finding; nothing regresses."""

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_every_assert_holds_after_the_remedies(self):
        results = _results(_load_model("payments_hardened.strata"))
        assert results["c_no_stripe_ledger"].verdict is Verdict.PROVED
        assert results["c_fresh_refund"].verdict is Verdict.PROVED
        assert results["c_no_browser_ledger"].verdict is Verdict.PROVED
        assert results["c_audit_path"].verdict is Verdict.PROVED

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_idempotent_consumer_clears_the_delivery_diagnostic(self):
        facts = build_facts(_load_model("payments_hardened.strata")).danger_ok
        assert facts.diagnostics == ()
