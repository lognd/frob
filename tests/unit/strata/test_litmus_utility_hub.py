"""T-0226 litmus pair: an unrelated utility/hub edge must not falsely
defeat a legitimate `noflow` claim once marked `utility;`, and must not
silently swallow a REAL transitive flow when left unmarked (mirroring
`test_litmus_host_isolation.py`'s parse -> elaborate -> evaluate
round-trip discipline: both fixtures run through the real `strata_core`
parser, never a hand-built `KernelModel`).

Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18):
graphite had to withdraw a TRUE `noflow` claim because SYS003 forced
declaring `tui -> core` (a logging import) and `core -> server`
(entrypoint hosting), and reachability closure treated the hub edge as
fully transitive, wrongly refuting the claim.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import Verdict, elaborate, evaluate_claims, parse_module

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _evaluate(filename: str):
    """Parse+elaborate+evaluate one `.strata` fixture under `litmus/` end to end."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    model = elaborate(module).danger_ok
    return evaluate_claims(model).danger_ok


class TestUtilityHubVulnLitmus:
    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_unmarked_hub_edge_refutes_the_noflow_claim(self):
        (result,) = _evaluate("utility_hub_vuln.strata")
        assert result.verdict is Verdict.REFUTED


class TestUtilityHubHardenedLitmus:
    # frob:tests src/frob/strata/_facts.py::FactBase.reachable kind="unit"
    def test_marked_utility_hub_edge_lets_the_noflow_claim_prove(self):
        (result,) = _evaluate("utility_hub_hardened.strata")
        assert result.verdict is Verdict.PROVED
