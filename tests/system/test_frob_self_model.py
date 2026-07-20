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


# frob:waive DUP001 reason="parallel CLI system-test scaffolding: \
# independent commands sharing the subprocess-dispatch arrange-act shape; \
# extracting would obscure per-command intent"
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
    # frob:tests strata-core/src/lib.rs kind="integration"
    # frob:tests strata-core/src/parse.rs kind="integration"
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
        # T-0150: 3 original PROVED architecture claims + 3 `assume
        # weakness:CWE-78:<node>` discharge claims that declaring `may
        # "exec"` on checker/core/vet (measured honestly, T-0150 Done
        # report) drags in via THREAT003 (docs/strata/threat.md
        # #capabilities-drag-in-obligations) = 6. T-0158: the exhaustive
        # dangerous-operations registry newly patterns sql/fetch_url/
        # deserialize (measured honestly, T-0158 Done report), adding
        # `may "sql"` to graphlang+vet and `may "fetch_url"`/
        # `may "deserialize"` to vet, which drags in 6 more discharge
        # claims (CWE-89 + CWE-639 for graphlang and vet each, plus
        # CWE-918 and CWE-502 for vet) = 12. T-0166: `store_prop` now
        # accepts `code`/`may` (docs/strata/surface.md#node-grammar-
        # implemented), un-folding `src/frob/tickets/**`'s code off `core`
        # onto `tickets_ledger`'s own `code`/`may` -- its `may "exec"`
        # drags in one more `weakness:CWE-78:tickets_ledger` discharge
        # claim = 13.
        assert len(_model.claims) == 13

    # frob:tests tests/system/test_frob_self_model.py::TestFrobSelfModel.test_every_claim_proves kind="e2e"
    def test_every_claim_proves(self, _model) -> None:
        """Every architecture claim this model draws holds today, and every
        T-0150 capability-discharge claim is a deliberately human-owned
        ASSUME (never silently PROVED, never REFUTED).

        A REFUTED claim here means either the model drifted from reality or
        a real regression (e.g. the `b_vet_endorse` boundary directive was
        deleted from `src/frob/vet/_registry.py`) -- either way, CI must
        fail loudly rather than let the claim silently stop meaning
        anything. The `weakness:CWE-78:*` claims are ASSUMEd, not PROVEd,
        by design (docs/strata/selfconform.md: `core`'s discharge
        specifically cannot be graph-proved, since `registry` DOES reach
        `core` transitively via `vet`; `tickets_ledger`'s IS graph-provable
        via `c_no_registry_ledger` but still follows the assume-for-
        uniformity precedent, T-0166) -- verified ASSUMED here rather than
        PROVED, and never REFUTED.
        """
        outcome = evaluate_claims(_model)
        assert outcome.is_ok, f"evaluate_claims failed: {outcome.err}"
        claim_results = outcome.danger_ok
        assert len(claim_results) == 13
        proved_ids = {
            "c_no_registry_ledger",
            "c_cache_derivable",
            "c_gates_reach_tickets",
        }
        assumed_ids = {
            "weakness:CWE-78:checker",
            "weakness:CWE-78:core",
            "weakness:CWE-78:vet",
            # T-0166: un-folding `src/frob/tickets/**` off `core` onto
            # `tickets_ledger`'s own code/may (see test_parses_and_
            # elaborates above for the full reasoning).
            "weakness:CWE-78:tickets_ledger",
            # T-0158: exhaustive registry additions (see test_parses_and_
            # elaborates above for the full reasoning).
            "weakness:CWE-89:graphlang",
            "weakness:CWE-639:graphlang",
            "weakness:CWE-89:vet",
            "weakness:CWE-639:vet",
            "weakness:CWE-918:vet",
            "weakness:CWE-502:vet",
        }
        seen_ids: set[str] = set()
        for claim_result in claim_results:
            seen_ids.add(claim_result.claim_id)
            assert claim_result.verdict != Verdict.REFUTED, (
                f"{claim_result.claim_id} REFUTED: {claim_result.detail}"
            )
            if claim_result.claim_id in proved_ids:
                assert claim_result.verdict == Verdict.PROVED, (
                    f"{claim_result.claim_id} did not prove: "
                    f"{claim_result.verdict} {claim_result.detail}"
                )
            else:
                assert claim_result.verdict == Verdict.ASSUMED, (
                    f"{claim_result.claim_id} expected ASSUMED, got "
                    f"{claim_result.verdict} {claim_result.detail}"
                )
        assert seen_ids == proved_ids | assumed_ids

    # frob:tests tests/system/test_frob_self_model.py::TestFrobSelfModel.test_sys_gate_zero_violations kind="e2e"
    # T-0365: TEST009 owes design/frob.strata itself an e2e binding, not
    # just a binding on the test method's own symbol (the directive above
    # marks the test as self-covering per the repo-wide idiom, but that
    # target never matches `_edges_for_design_file`'s design-file prefix
    # check). This is the one test in the suite that runs frob's real
    # `build_graph` + `sys_gate` path against this repo's own live
    # `design/frob.strata`, so it is the correct e2e evidence for the
    # design file as a deployable artifact.
    # frob:tests design/frob.strata kind="e2e"
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
