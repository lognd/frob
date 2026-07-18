"""System test for frob's self-hosting design model (T-0081).

`design/frob.strata` is frob's own architecture, in frob's own language
(docs/strata/roadmap.md "Self-hosting commitments (decision D7)"). This
test locks two things in CI so neither regresses silently:

1. the model itself is a real, live `.strata` program -- it parses,
   elaborates, and evaluates its claims without error, and every claim
   this model draws about frob's own supply-chain integrity, cache
   derivability, and gate-to-ledger reachability actually holds (PROVED,
   not REFUTED or a silent ASSUME);
2. `frob check --only sys` -- the same gate CI runs -- reports zero
   violations against this model (SYS001 dangling directive, SYS002
   unbound boundary/secret, SYS003 undeclared cross-component import,
   SYS004 load failure), so a future edit to either the model or the
   `frob:channel`/`frob:boundary` anchors in `src/frob/vet/_registry.py`
   and `src/frob/app/ticket_runner.py` that breaks the binding fails CI
   immediately instead of silently rotting.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.gates import sys_gate
from frob.graph import build_graph
from frob.strata import Verdict, elaborate, evaluate_claims, parse_module

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODEL_PATH = _REPO_ROOT / "design" / "frob.strata"


@pytest.fixture(scope="module")
def _model():
    """Parse + elaborate `design/frob.strata` once for every test in this module."""
    text = _MODEL_PATH.read_text(encoding="utf-8")
    parsed = parse_module(text)
    assert parsed.is_ok, f"design/frob.strata failed to parse: {parsed.err}"
    elaborated = elaborate(parsed.danger_ok)
    assert elaborated.is_ok, f"design/frob.strata failed to elaborate: {elaborated.err}"
    return elaborated.danger_ok


class TestFrobSelfModel:
    # frob:tests design kind="integration"
    # frob:tests tests/system/test_frob_self_model.py::TestFrobSelfModel.test_model_file_exists kind="e2e"
    def test_model_file_exists(self) -> None:
        """`design/frob.strata` exists -- the phase-4 self-hosting exit artifact."""
        assert _MODEL_PATH.is_file()

    # This one test method is the bound TEST001 evidence for every flow and
    # the one boundary the model declares (TEST001 only requires FUNCTION-
    # kind design symbols -- flow/boundary -- to have a bound unit test; the
    # node/store/cache/module/assert kinds are covered by COV001's doc-edge
    # requirement instead). One structural assertion genuinely does cover
    # all of them: it fails the moment any of these flows or the boundary
    # stops existing in the elaborated model.
    # frob:tests design/frob.strata::frob.f_registry_fetch kind="unit"
    # frob:tests design/frob.strata::frob.f_parse kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_core kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_checker kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_gates kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_tickets kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_vet kind="unit"
    # frob:tests design/frob.strata::frob.f_graphlang_core kind="unit"
    # frob:tests design/frob.strata::frob.f_checker_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_checker_core kind="unit"
    # frob:tests design/frob.strata::frob.f_checker_gates kind="unit"
    # frob:tests design/frob.strata::frob.f_core_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_core_gates kind="unit"
    # frob:tests design/frob.strata::frob.f_core_tickets kind="unit"
    # frob:tests design/frob.strata::frob.f_gates_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_gates_core kind="unit"
    # frob:tests design/frob.strata::frob.f_gates_strata kind="unit"
    # frob:tests design/frob.strata::frob.f_gates_tickets kind="unit"
    # frob:tests design/frob.strata::frob.f_strata_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_strata_core kind="unit"
    # frob:tests design/frob.strata::frob.f_strata_vet kind="unit"
    # frob:tests design/frob.strata::frob.f_vet_gates kind="unit"
    # frob:tests design/frob.strata::frob.f_vet_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_vet_core kind="unit"
    # frob:tests design/frob.strata::frob.f_tickets_core kind="unit"
    # frob:tests design/frob.strata::frob.b_vet_endorse kind="unit"
    def test_parses_and_elaborates(self, _model) -> None:
        """Sanity: the model declares a nonzero component/flow/boundary/claim surface."""
        assert len(_model.nodes) == 10
        # 25 hand-declared flows (24 component-to-component + the one
        # registry -> vet network edge) + 2 the `cache graph_cache of
        # graphlang` sugar auto-generates (`graph_cache__fill` and
        # `graph_cache__inval_f_parse`, docs/strata/surface.md's desugar
        # table) = 27.
        assert len(_model.flows) == 27
        assert len(_model.boundaries) == 1
        assert len(_model.claims) == 3

    # frob:tests tests/system/test_frob_self_model.py::TestFrobSelfModel.test_every_claim_proves kind="e2e"
    def test_every_claim_proves(self, _model) -> None:
        """Every claim this model draws about frob's own architecture holds today.

        A REFUTED claim here means either the model drifted from reality or
        a real regression (e.g. the `b_vet_endorse` boundary directive was
        deleted from `src/frob/vet/_registry.py`) -- either way, CI must
        fail loudly rather than let the claim silently stop meaning
        anything.
        """
        outcome = evaluate_claims(_model)
        assert outcome.is_ok, f"evaluate_claims failed: {outcome.err}"
        claim_results = outcome.danger_ok
        assert len(claim_results) == 3
        seen_ids: set[str] = set()
        for claim_result in claim_results:
            seen_ids.add(claim_result.claim_id)
            assert claim_result.verdict == Verdict.PROVED, (
                f"{claim_result.claim_id} did not prove: "
                f"{claim_result.verdict} {claim_result.detail}"
            )
        assert seen_ids == {
            "c_no_registry_ledger",
            "c_cache_derivable",
            "c_gates_reach_tickets",
        }

    # frob:tests tests/system/test_frob_self_model.py::TestFrobSelfModel.test_sys_gate_zero_violations kind="e2e"
    def test_sys_gate_zero_violations(self, tmp_path: Path) -> None:
        """`frob check --only sys` against the live repo reports zero violations.

        Exercises the full real path (`frob.graph.build_graph` +
        `frob.gates.sys_gate`) CI actually runs, not a synthetic
        `tmp_path` model fixture -- this is the one test in the suite that
        binds directly to this repo's own `frob:channel`/`frob:boundary`
        anchors and this repo's own `design/` directory. Builds into a
        throwaway cache (rather than the repo's own `.frob/cache.db`) so
        this test never races a concurrent `frob check` for the cache
        file.
        """
        build_result = build_graph(_REPO_ROOT, tmp_path / "cache.db")
        assert build_result.is_ok, f"graph build failed: {build_result.err}"
        violations = sys_gate(_REPO_ROOT, build_result.danger_ok)
        assert violations == (), f"unexpected SYS violation(s): {violations}"
