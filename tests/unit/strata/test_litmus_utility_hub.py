"""T-0226 litmus pair, corrected by T-0496 (docs/audits/strata.md G5):
`utility_hub_vuln.strata` (unmarked hub, REFUTED -- unaffected by T-0496)
and `utility_hub_hardened.strata` (marked hub, now discharged via a REAL
ENDORSE boundary rather than the `utility` marker alone) -- mirroring
`test_litmus_host_isolation.py`'s parse -> elaborate -> evaluate round-trip
discipline: both fixtures run through the real `strata_core` parser, never
a hand-built `KernelModel`.

Filed from sibling-repo pilot P1 (graphite/feldspar/lithos, 2026-07-18):
graphite had to withdraw a TRUE `noflow` claim because SYS003 forced
declaring `tui -> core` (a logging import) and `core -> server`
(entrypoint hosting), and reachability closure treated the hub edge as
fully transitive, wrongly refuting the claim. T-0226's original fix (mark
the hub edge `utility;` to make it terminal even for the confidentiality
closure) turned out to be unsound: a T-0401 audit (G5) found this let a
REAL downstream leak through the exact same hub hide from `noflow`
entirely (`test_claims.py::TestNoFlow.
test_real_leak_through_a_utility_hub_still_refutes` is the minimal,
non-fixture litmus for that). `utility` is no longer honored for the
confidentiality closure at all (`_facts.py::_NOFLOW_NON_TRANSITIVE_ATTRS`)
-- `utility_hub_hardened.strata` now discharges via a real boundary
instead, the only sound mechanism.
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
        """T-0496: the `utility` marker on `f_tui_logs` is present but INERT
        for this claim -- the real ENDORSE boundary on `f_logs_server` is
        what discharges it now, module docstring's correction."""
        (result,) = _evaluate("utility_hub_hardened.strata")
        assert result.verdict is Verdict.PROVED
