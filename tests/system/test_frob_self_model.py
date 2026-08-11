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


# frob:ticket T-1079
class TestFrobSelfModel:
    # frob:tests design kind="integration"
    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModel.test_model_file_exists \
    # kind="e2e"
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
    # frob:tests design/frob.strata::frob.f_cli_registry_model kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_fleet kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_deploy kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_mutate kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_serve kind="unit"
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
    # frob:tests design/frob.strata::frob.f_gates_registry_model kind="unit"
    # frob:tests design/frob.strata::frob.f_strata_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_strata_core kind="unit"
    # frob:tests design/frob.strata::frob.f_strata_vet kind="unit"
    # frob:tests design/frob.strata::frob.f_vet_gates kind="unit"
    # frob:tests design/frob.strata::frob.f_vet_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_vet_core kind="unit"
    # frob:tests design/frob.strata::frob.f_tickets_core kind="unit"
    # frob:tests design/frob.strata::frob.f_fleet_tickets kind="unit"
    # frob:tests design/frob.strata::frob.f_fleet_core kind="unit"
    # frob:tests design/frob.strata::frob.f_deploy_strata kind="unit"
    # frob:tests design/frob.strata::frob.f_deploy_core kind="unit"
    # frob:tests design/frob.strata::frob.f_mutate_core kind="unit"
    # frob:tests design/frob.strata::frob.f_serve_core kind="unit"
    # frob:tests design/frob.strata::frob.f_serve_gates kind="unit"
    # frob:tests design/frob.strata::frob.f_serve_graphlang kind="unit"
    # frob:tests design/frob.strata::frob.f_serve_tickets kind="unit"
    # frob:tests design/frob.strata::frob.f_cli_natives kind="unit"
    # frob:tests design/frob.strata::frob.f_natives_core kind="unit"
    # frob:tests design/frob.strata::frob.b_vet_endorse kind="unit"
    # frob:tests strata-core/src/lib.rs kind="integration"
    # frob:tests strata-core/src/parse.rs kind="integration"
    # frob:ticket T-1079
    def test_parses_and_elaborates(self, _model) -> None:
        """Sanity: the model declares a nonzero component/flow/boundary/claim surface.

        T-0440: `deploy`/`serve`/`mutate` split off `core`'s former
        utility-hub node into three standalone components. This test's
        node/flow/claim counts were ALREADY stale against the pre-T-0440
        tree before this ticket touched them (12/32/24 measured directly
        via `elaborate`, not the 10/27/23 previously asserted here --
        `fleet`'s T-0707 `may "exec"` addition and its
        `weakness:CWE-78:fleet` discharge claim were never folded into
        this docstring's running count) -- disclosed as pre-existing debt
        in the T-0440 Done report, not introduced by this ticket. T-0440
        itself adds 3 nodes (12 -> 15), 10 hand-declared flows (32 -> 42:
        `f_cli_deploy`/`f_cli_mutate`/`f_cli_serve` inbound from `cli`,
        `f_deploy_strata`/`f_deploy_core`/`f_mutate_core`/`f_serve_core`/
        `f_serve_gates`/`f_serve_graphlang`/`f_serve_tickets` outbound),
        and 2 THREAT003 discharge claims (24 -> 26:
        `weakness:CWE-78:deploy`/`weakness:CWE-78:mutate` -- both newly
        declare `may "exec"`; `serve` declares no `may` atom at all, so it
        drags in zero).

        T-0967: same drift again, this time from T-0864's `natives` node
        (`frob natives build`, design/frob.strata `node natives`) -- it
        was never folded into this docstring's running count either: +1
        node (15 -> 16), +2 hand-declared flows (42 -> 44:
        `f_cli_natives`/`f_natives_core`), and +1 THREAT003 discharge
        claim (26 -> 27: `weakness:CWE-78:natives`, `natives` declares
        `may "exec"` with no `may "eval"`, so it drags in no CWE-94 pair).

        T-1079 (SYS103's 264-finding follow-up, docs/modules/strata.md's
        "Modeled: `_PACKAGE_ROOT` restriction's 264-finding follow-up"):
        +4 nodes (16 -> 20: `testsuite`/`scripts_ops`/
        `strata_core_native`/`frob_core_native`, binding `tests/**`/
        `scripts/**`/`strata-core/src/**`/`frob-core/src/**` -- none had
        an owning node before), +0 hand-declared flows (44 -> 44: none
        of the four is on the cli-dispatch/component-import graph the
        `f_*` flows model, so none gets one), and +4 THREAT003 discharge
        claims (27 -> 31: `weakness:CWE-78:testsuite`/`weakness:
        CWE-89:testsuite`/`weakness:CWE-918:testsuite`/`weakness:
        CWE-502:testsuite` -- `testsuite` is the only one of the four new
        nodes whose declared `may` set drags in an owasp-top-10
        obligation; `scripts_ops`'s `fs`/`fs-read` and
        `strata_core_native`/`frob_core_native`'s `ffi` do not).

        T-2102: this docstring's "landed a node/flow/claim, forgot to
        bump the counter" gap recurred at T-0707, T-0864, T-1329,
        T-1591, and again silently between T-1735 and this ticket (23 ->
        25 nodes measured directly, with `test_every_claim_proves`'s own
        `len(claim_results) == 31` failing the same way, 31 -> 34) --
        five independent, disclosed instances of the exact same
        maintenance cost. A hardcoded exact count that must be
        hand-rederived every time the self-hosting model legitimately
        grows is a standing trap, not a one-off oversight: it fails
        every organic addition exactly as loudly as a real regression,
        so a maintainer's trained response becomes "bump the number,"
        which is precisely how five previous drifts went undetected for
        as long as they did.

        Replaced the exact `==` counts below with `>=` FLOORS (this
        test's actual job, per its own module docstring, is "the model
        is a real, live program that parses and elaborates without
        error" -- growth is expected and healthy; only SHRINKAGE, which
        `elaborate` cannot itself detect since removing a node/flow/
        claim is a perfectly valid edit, is the real regression this
        sanity check exists to catch). `elaborate` already fails closed
        on the corruption shapes a count COULD have caught incidentally
        (`_validate_no_duplicates`: duplicate node/flow/secret ids;
        dangling flow/boundary references) -- see `_model`'s own
        fixture, which asserts `elaborated.is_ok` and would already fail
        this test first were either to happen. The floor values below
        are this ticket's own measured counts (2026-08-10), not the
        pre-ticket stale ones.
        """
        # T-1329: +1 node = `refactor` (the T-1197 rewrite engine, modeled
        # after landing unbound; SYS102 fallout from the T-1320 coverage run).
        # T-1591: +1 node = `security` (src/frob/security/** extracted
        # from gates/_pii_structural.py, T-1318 -- pure regex/string
        # logic with no `may` capabilities or flows of its own, so only
        # the node count moves; T-1589 already re-derived the k8s/seccomp
        # export goldens for this same addition but missed this counter).
        # T-1735 (found live, T-1687 pre-existing debt this docstring never
        # re-measured until this pass surfaced it -- same "landed a node,
        # missed the self-model counter" shape as T-1591/T-1329 above):
        # +1 node = `verify` (T-1687's durable commit-keyed verify queue,
        # `node verify : trusted` in design/frob.strata) -- declares no
        # `may` capability and is not on the cli-dispatch/component-import
        # graph the `f_*` flows model, so flows/boundaries/claims counts
        # below are unaffected; only the node count moves, 22 -> 23.
        # T-2102: floors, not exact counts -- see the docstring's T-2102
        # paragraph above for why. 23/44/1 was the pre-T-2102 count;
        # measured 25/44/1 as of this ticket (2 organic node additions,
        # 0 new flows/boundaries).
        assert len(_model.nodes) >= 25
        assert len(_model.flows) >= 44
        assert len(_model.boundaries) >= 1
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
        # claim = 13. T-0401 (G3): `eval` joined to CWE-94 and CWE-78 in
        # CWE_CATALOG, dragging in CWE-94 discharges for every
        # eval-declaring node (cli/graphlang/stratamod/core/
        # tickets_ledger) plus fresh CWE-78 discharges for the
        # eval-only nodes (cli/graphlang/stratamod) = 21. T-0443: `gates`
        # gained `may "eval"` (importlib of the [[docblocks.commands]]
        # parser source), dragging in its own CWE-94 + CWE-78 pair = 23.
        # T-0707 (fleet, already-landed pre-T-0440 debt this docstring had
        # never re-measured): `fleet` gained `may "exec"`, dragging in its
        # own `weakness:CWE-78:fleet` discharge = 24 (the real pre-T-0440
        # count). T-0440: `deploy` and `mutate` both newly declare
        # `may "exec"` (see module docstring above), each dragging its own
        # `weakness:CWE-78:<node>` discharge = 26. `serve` declares no
        # `may` atom, so it drags in zero. T-0864 (pre-existing debt this
        # docstring never re-measured until T-0967's own pass surfaced it,
        # same shape as T-0707's `fleet` gap above): `natives` newly
        # declares `may "exec"` (`build_natives`'s maturin/cargo subprocess
        # calls, docs/modules/cli.md#frob-natives-build-t-0864), dragging
        # in its own `weakness:CWE-78:natives` discharge = 27. T-1079
        # (SYS103's 264-finding follow-up, see module docstring above):
        # `testsuite` (`code "tests/**"`) newly declares `exec`/`eval`/
        # `sql`/`fetch_url`/`net`/`deserialize`, dragging in 4 discharge
        # claims (owasp-top-10 view: CWE-78, CWE-89, CWE-918, CWE-502 --
        # CWE-94/CWE-639 are not in that view, same reasoning `cli`'s own
        # T-0401 comment above already documents) = 31. `scripts_ops`
        # (`fs`/`fs-read`) and `strata_core_native`/`frob_core_native`
        # (`ffi`) drag in none.
        # T-2102: floor, not exact count -- 31 was the pre-T-2102 count,
        # measured 34 as of this ticket (see the T-2102 docstring
        # paragraph above).
        assert len(_model.claims) >= 31

    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModel.test_every_claim_proves \
    # kind="e2e"
    # frob:ticket T-1079
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

        T-0440: this test's `assumed_ids` set was already missing
        `weakness:CWE-78:fleet` (T-0707's `fleet` node has declared
        `may "exec"` since before this ticket) -- pre-existing debt this
        ticket's own re-measurement surfaced and fixed, disclosed in the
        Done report. T-0440 itself adds `weakness:CWE-78:deploy` and
        `weakness:CWE-78:mutate` (see `deploy`/`mutate`'s own `assume`
        directives in design/frob.strata for the per-node reasoning);
        `serve` declares no `may` atom, so it drags in no discharge claim.

        T-0967: same drift shape again -- `weakness:CWE-78:natives` was
        missing here (T-0864's `natives` node has declared `may "exec"`
        with its own `assume "weakness:CWE-78:natives"` directive in
        design/frob.strata since before this ticket, but this test's
        hardcoded counts/sets were never re-measured against it) --
        pre-existing model-vs-test drift this ticket root-caused and
        fixed, not a real prover regression (no claim REFUTEs; the model
        itself already carried the correct assume).

        T-1079: `testsuite`'s 4 new discharge claims (CWE-78/89/918/502,
        see test_parses_and_elaborates' docstring above) were added to
        this test's `assumed_ids` set -- genuine model growth, not
        drift, since `testsuite` (`code "tests/**"`) did not exist in
        the model before this ticket.

        T-2102: dropped the hardcoded `assumed_ids` enumeration and the
        `seen_ids == proved_ids | assumed_ids` exact-set check that used
        to sit on top of the per-claim loop below. That equality check
        added NO safety the loop did not already provide -- every claim
        result was already checked (never REFUTED; PROVED iff its id is
        in `proved_ids`; ASSUMED otherwise, unconditionally, regardless
        of set membership) -- it only tested "did the hardcoded set
        enumerate every claim id that exists today," which is exactly
        the golden-drift trap `test_parses_and_elaborates`' own T-2102
        paragraph documents (five independent, disclosed misses:
        T-0707, T-0864, T-1329, T-1591, and the 23-vs-25 node drift this
        ticket fixed). `proved_ids` stays hardcoded and enumerated
        deliberately: those three ids are the model's only claims meant
        to be graph-PROVED rather than human-ASSUMED, a real, narrow
        invariant worth locking by name -- unlike `assumed_ids`, growing
        that set is not this test's job.
        """
        outcome = evaluate_claims(_model)
        assert outcome.is_ok, f"evaluate_claims failed: {outcome.err}"
        claim_results = outcome.danger_ok
        # T-2102: floor, not exact count -- see test_parses_and_
        # elaborates' own T-2102 paragraph for why (31 was the
        # pre-T-2102 count, measured 34 as of this ticket).
        assert len(claim_results) >= 31
        proved_ids = {
            "c_no_registry_ledger",
            "c_cache_derivable",
            "c_gates_reach_tickets",
        }
        seen_proved_ids: set[str] = set()
        for claim_result in claim_results:
            assert claim_result.verdict != Verdict.REFUTED, (
                f"{claim_result.claim_id} REFUTED: {claim_result.detail}"
            )
            if claim_result.claim_id in proved_ids:
                seen_proved_ids.add(claim_result.claim_id)
                assert claim_result.verdict == Verdict.PROVED, (
                    f"{claim_result.claim_id} did not prove: "
                    f"{claim_result.verdict} {claim_result.detail}"
                )
            else:
                assert claim_result.verdict == Verdict.ASSUMED, (
                    f"{claim_result.claim_id} expected ASSUMED, got "
                    f"{claim_result.verdict} {claim_result.detail}"
                )
        # Every one of the 3 known-provable claims still exists and
        # still resolved PROVED above -- a deleted/renamed proof target
        # would otherwise pass silently (the loop above only checks ids
        # it SEES; this catches one going missing entirely).
        assert seen_proved_ids == proved_ids

    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModel.test_sys_gate_zero_violat\
    # ions kind="e2e"
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
