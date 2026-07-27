"""Surface-syntax tube (video platform) litmus goldens (T-0072).

Phase-2 exit criterion (docs/strata/roadmap.md#the-litmus-program):
`design/litmus/tube.strata` must reproduce, end to end through
`parse_module -> elaborate -> evaluate_claims`, the stampede/cold-cache
shape, the immutable-TTL pairing, CDN TLS termination as declassification,
and a money-grade payout node fed only by an approximate counter path.
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
    StrataError,
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

# The naive twin of tube.strata's session/CDN pair, with
# `tls_terminates_at_provider` removed from the cdn block. This is a
# hand-written literal (not a second tracked file) purely to demonstrate
# that the committed model's PROVED verdict on c_no_session_on_cdn is
# earned by the declassify boundary, not by an absent taint path -- delete
# the one line and it flips straight to REFUTED with the same witness the
# committed file's docstring describes.
_NAIVE_SESSION_CDN = """
module tube_naive
node browser : foreign { clearance Public; }
store origin : trusted { clearance Internal; engine content_addressed; immutable; }
cdn edge of origin { provider fastly : authenticated; staleness unlimited; hit 97 %; }
store sessions : trusted { clearance Secret; }
flow f_sess_personalize : sessions -> origin { label Secret; }
assert c_no_session_on_cdn noflow sessions -> edge
"""

# A mutable origin paired with `staleness unlimited`: illegal per the
# immutable-TTL pairing (docs/strata/surface.md#the-immutable-ttl-pairing).
_MUTABLE_UNLIMITED_CDN = """
module tube_bad
store origin_mutable : trusted { clearance Internal; engine content_addressed; }
cdn edge_bad of origin_mutable {
    provider fastly : authenticated;
    staleness unlimited;
}
"""


def _load_model() -> KernelModel:
    text = (_LITMUS_DIR / "tube.strata").read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    return elaborate(module).danger_ok


def _results(model: KernelModel) -> dict[str, ClaimResult]:
    evaluated = evaluate_claims(model, today=_TODAY).danger_ok
    return {r.claim_id: r for r in evaluated}


class TestTubeGoldens:
    """design/litmus/tube.strata claim verdicts, evaluated end to end."""

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_payout_age_bound_refutes_off_the_approximate_counter_path(self):
        result = _results(_load_model())["c_payout_freshness"]
        assert result.verdict is Verdict.REFUTED
        assert result.quantifier is Quantifier.FORALL
        assert "300.0s > 60.0s" in result.detail
        assert result.counterexample == (
            "view_counter",
            "view_agg__fill",
            "view_agg",
            "f_payout_read",
            "payout",
        )

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_session_noflow_proves_because_tls_terminates_at_provider_declassifies(
        self,
    ):
        result = _results(_load_model())["c_no_session_on_cdn"]
        assert result.verdict is Verdict.PROVED
        assert result.quantifier is Quantifier.FORALL

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_session_noflow_refutes_without_the_tls_terminates_declassify(self):
        """Same session/origin/cdn shape, minus `tls_terminates_at_provider`.

        Proves the committed file's PROVED verdict is earned by the
        declassify boundary, not by an absent taint path: remove the one
        line and the exact same claim flips to REFUTED with the
        sessions -> origin -> edge witness.
        """
        module = parse_module(_NAIVE_SESSION_CDN).danger_ok
        model = elaborate(module).danger_ok
        result = _results(model)["c_no_session_on_cdn"]
        assert result.verdict is Verdict.REFUTED
        assert result.counterexample == (
            "sessions",
            "f_sess_personalize",
            "origin",
            "edge__fill",
            "edge",
        )

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    # frob:tests src/frob/strata/_elaborate.py::elaborate kind="unit"
    def test_watch_capacity_utilization_is_proved(self):
        result = _results(_load_model())["c_watch_capacity"]
        assert result.verdict is Verdict.PROVED
        assert "75.0%" in result.detail

    # frob:tests src/frob/strata/_infra.py::elaborate_infra kind="unit"
    def test_mutable_origin_with_unlimited_staleness_is_illegal(self):
        """The commented-out mutable variant in tube.strata, run for real.

        `staleness unlimited` is legal only over an `immutable` source
        (docs/strata/surface.md#the-immutable-ttl-pairing); this is the
        illegal pairing the comment in tube.strata describes, exercised as
        an actual elaboration instead of staying inert prose.
        """
        module = parse_module(_MUTABLE_UNLIMITED_CDN).danger_ok
        result = elaborate(module)
        assert result.is_err
        assert result.danger_err is StrataError.MutableUnbounded

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_session_write_into_origin_exceeds_clearance_diagnostic(self):
        """The session-into-origin write is flagged as a structural finding.

        `f_sess_personalize` carries label Secret into `origin` (clearance
        Internal) -- exactly the antipattern this litmus models, and
        `build_facts` must flag it even though the noflow claim above
        separately proves via the declassify boundary.
        """
        facts = build_facts(_load_model()).danger_ok
        assert any(
            "f_sess_personalize" in d and "exceeds clearance" in d
            for d in facts.diagnostics
        )
