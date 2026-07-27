"""Surface-syntax chirp (timeline fanout) litmus goldens (T-0072).

Phase-2 exit criterion (docs/strata/roadmap.md#the-litmus-program):
`design/litmus/chirp.strata` must reproduce, end to end through
`parse_module -> elaborate -> evaluate_claims`, the "averages-lie" golden
(a zipf-skewed hottest shard refutes where an identical mean-based twin
proves) and a growth-horizon claim that flips a passing utilization to
REFUTED once compound growth crosses the 24-month saturation horizon.
These goldens are permanent CI fixtures: a language change that stops one
of these findings from firing is a regression, not a feature.
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
)

_TODAY = dt.date(2026, 7, 17)


# frob:waive DUP001 reason="parallel litmus scenario fixtures: 7 sites across 7 \
# file(s) sharing the exhaustiveness-fixture arrange-act shape by design (store-backed \
# vs non-store-backed, or per-CWE scenario variants); extracting would obscure \
# per-scenario intent"
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


def _load_model() -> KernelModel:
    text = (_LITMUS_DIR / "chirp.strata").read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


def _results(model: KernelModel) -> dict[str, ClaimResult]:
    evaluated = evaluate_claims(model, today=_TODAY).danger_ok
    return {r.claim_id: r for r in evaluated}


class TestChirpGoldens:
    """design/litmus/chirp.strata claim verdicts, evaluated end to end."""

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    # frob:waive DUP001 reason="parallel litmus scenario fixtures: 2 sites across 1 \
    # file(s) sharing the exhaustiveness-fixture arrange-act shape by design \
    # (store-backed vs non-store-backed, or per-CWE scenario variants); extracting \
    # would obscure per-scenario intent"
    def test_hottest_shard_utilization_refutes_under_zipf_skew(self):
        result = _results(_load_model())["c_hot_shard_utilization"]
        assert result.verdict is Verdict.REFUTED
        assert result.quantifier is Quantifier.FORALL
        assert "89.8%" in result.detail
        assert "hottest-shard share" in result.detail
        assert "zipf alpha=1.5" in result.detail

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_mean_based_twin_proves_the_averages_lie_golden(self):
        """Same aggregate demand and capacity as the hot shard, no `skew`.

        The mean-based ceiling call this PROVED at 37.5% while the zipf
        skew twin above REFUTES at the identical demand -- the
        "averages lie" contrast is the golden this test pins down.
        """
        result = _results(_load_model())["c_mean_shard_utilization"]
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.FORALL
        assert "37.5%" in result.detail

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    # frob:waive DUP001 reason="parallel litmus scenario fixtures: 2 sites across 1 \
    # file(s) sharing the exhaustiveness-fixture arrange-act shape by design \
    # (store-backed vs non-store-backed, or per-CWE scenario variants); extracting \
    # would obscure per-scenario intent"
    def test_growth_horizon_flips_a_passing_utilization_to_refuted(self):
        result = _results(_load_model())["c_growth_shard_utilization"]
        assert result.verdict is Verdict.REFUTED
        assert result.quantifier is Quantifier.FORALL
        assert "saturates in" in result.detail
        assert "months" in result.detail
        assert "2026-09" in result.detail

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_no_structural_diagnostics(self):
        facts = build_facts(_load_model()).danger_ok
        assert facts.diagnostics == ()
