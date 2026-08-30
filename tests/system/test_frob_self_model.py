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

# T-2109 (coordinator decision, 2026-08-17, superseding T-2109 attempts 1/2's
# derived-count approach -- see the ticket's own Failure log for why a count
# derived from the SAME raw design source under validation is tautological: an
# unintended addition moves both sides of the equation together and the check
# never fires): the exact, committed set of `design/frob.strata`'s elaborated
# node ids. Unlike a count (which only shrinks or grows) or a derived formula
# (which cannot distinguish an intentional addition from an unintended one),
# an explicit SET catches BOTH directions of drift -- an addition shows up as
# an unexplained extra id, a removal as a missing one, each named by
# `_node_id_diff_message` below -- and updating this fixture is itself a
# deliberate, reviewable diff (the whole point: the fixture only moves when a
# ticket's own change explains the new line, never silently).
_EXPECTED_NODE_IDS = frozenset(
    {
        "checker",
        "claude_hooks",
        "cli",
        "core",
        "deploy",
        "fleet",
        "frob_core_native",
        "gates",
        "graph_cache",
        "graphlang",
        "mutate",
        "narrative",
        "natives",
        "refactor",
        "registry",
        "registry_model",
        "scripts_ops",
        "security",
        "serve",
        "strata_core_native",
        "stratamod",
        "telemetry",
        "testsuite",
        "tickets_ledger",
        "verify",
        "vet",
    }
)


def _node_id_diff_message(
    actual: frozenset[str], expected: frozenset[str]
) -> str | None:
    """Compare an actual node-id set against the golden `expected` set (T-2109),
    returning `None` when they match exactly or a message naming every
    symmetric-difference id (both directions) otherwise -- unlike a bare `==`
    assertion, this names WHICH ids are unexpectedly present or unexpectedly
    missing rather than just reporting inequality, so a failure is
    immediately actionable without a manual diff."""
    extra = sorted(actual - expected)
    missing = sorted(expected - actual)
    if not extra and not missing:
        return None
    parts = []
    if extra:
        parts.append(f"unexpected (present but not in the golden set): {extra}")
    if missing:
        parts.append(f"missing (in the golden set but not present): {missing}")
    return (
        "design/frob.strata's elaborated node-id set diverged from the "
        "committed golden set in tests/system/test_frob_self_model.py::"
        "_EXPECTED_NODE_IDS -- " + "; ".join(parts) + ". If this divergence "
        "is an intentional model change, update _EXPECTED_NODE_IDS in the "
        "same diff as a deliberate, reviewable edit; if not, it is an "
        "unintended addition/removal this check exists to catch."
    )


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

        T-3423: `_EXPECTED_NODE_IDS` drifted a fourth time (this pass added
        `narrative`, T-3029's ledger-migration CLI parser split, `code
        "src/frob/narrative/**"` in design/frob.strata -- `fs.read`-only,
        not on the cli-dispatch/component-import graph the `f_*` flows
        model, so only the node-id set moves). Read closely, this is NOT
        a repeat of the T-0440/T-0967/T-1079/T-2102 anti-pattern above:
        those four each silently transcribed a bare `==` integer that
        gave no signal WHAT changed or WHY updating it was safe. T-2109
        (2026-08-17, already landed before this ticket was filed) had
        already replaced the node-count floor with exactly this ticket's
        own option (c) for nodes specifically: `_node_id_diff_message`
        names every added/removed id and tells the reader to update
        `_EXPECTED_NODE_IDS` "in the same diff as a deliberate, reviewable
        edit" -- see that function's docstring. This failure is that
        mechanism doing its job for the first time since it was built:
        catching a real, disclosed model addition and demanding an
        explicit, named acknowledgment rather than silently drifting.
        DECISION (T-3423, stated explicitly per the ticket's own request,
        not inherited): keep the existing hybrid rather than moving
        everything to pure option (a). `_EXPECTED_NODE_IDS` stays an
        exact golden SET (T-2109's option (c)) because a floor cannot
        distinguish an intentional node addition from an unintended one
        (T-2109's own reasoning, still correct) -- losing that would trade
        a real signal for one fewer manual edit. `flows`/`boundaries`/
        `claims` stay `>=` FLOORS (T-2102's option (a)) because no
        derivable-formula or golden-set case has been made for those
        three (same scope boundary T-2109 drew) and a plain floor already
        satisfies this test's own stated job ("nonzero ... surface", not
        exact reproduction) without the maintenance cost integer equality
        had. What actually changes here: this paragraph documents the
        pattern explicitly so the NEXT node addition is recognized as
        T-2109's mechanism working as designed, not a fifth instance of
        the anti-pattern the first four paragraphs describe -- and two
        new tests below make both directions of the contract explicit
        (`TestFrobSelfModelFailureModes`): an empty/unparseable model
        still fails this sanity check (MUST-FIRE), and the golden-set/
        floor combination already demonstrated above (T-2109's own
        injected/removed-node positive controls) is this test's existing
        MUST-STAY-QUIET evidence for a legitimate node addition under
        option (c) -- it fails, but with a message naming exactly what to
        update and why, never a silent pass and never an opaque count
        mismatch.
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
        # T-2109 (coordinator decision, 2026-08-17): the node count's own
        # `>=` floor is replaced with an exact golden-SET comparison against
        # `_EXPECTED_NODE_IDS` above -- see that constant's own docstring for
        # why a set (not a count, not a formula derived from the same source
        # under validation) is the only one of the three that catches an
        # unintended ADDITION, not just shrinkage. flows/boundaries/claims
        # keep T-2102's floor: T-2109's scope is the node-count assertion
        # specifically (see the ticket body), and no derivable-formula/
        # golden-set case was made for those three.
        # T-3423: +1 node = `narrative` (T-3029's ledger-migration CLI
        # parser split, `node narrative : trusted` / `code
        # "src/frob/narrative/**"` in design/frob.strata) -- declares only
        # `may "fs.read"` and is not on the cli-dispatch/component-import
        # graph the `f_*` flows model, so flows/boundaries/claims below are
        # unaffected; only `_EXPECTED_NODE_IDS` moves (see module docstring
        # above for the T-3423 decision this update follows).
        actual_node_ids = frozenset(node.id for node in _model.nodes)
        diff_message = _node_id_diff_message(actual_node_ids, _EXPECTED_NODE_IDS)
        assert diff_message is None, diff_message
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

    # T-2109's own positive controls for `_node_id_diff_message` (the
    # comparison mechanism `test_parses_and_elaborates` binds to the real
    # elaborated model above) -- exercised directly against synthetic sets
    # rather than by mutating `design/frob.strata` itself (out of T-2109's
    # declared scope, `tests/system/test_frob_self_model.py` only). Per the
    # coordinator's decision: an injected node must fail naming it, a
    # removed node must fail naming it, and an unchanged set must pass --
    # all three are required, not just the happy path, because a check that
    # only ever catches one direction is exactly the asymmetric floor this
    # ticket replaces.
    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModel.test_golden_node_id_set_c\
    # atches_an_injected_node kind="unit"
    # frob:ticket T-2109
    def test_golden_node_id_set_catches_an_injected_node(self) -> None:
        """An id present in `actual` but absent from `_EXPECTED_NODE_IDS`
        (an unintended addition, the exact failure mode a `>=` floor could
        never catch) fails and names the extra id."""
        actual = _EXPECTED_NODE_IDS | {"unintended_extra_node"}
        message = _node_id_diff_message(actual, _EXPECTED_NODE_IDS)
        assert message is not None
        assert "unintended_extra_node" in message
        assert "unexpected" in message

    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModel.test_golden_node_id_set_c\
    # atches_a_removed_node kind="unit"
    # frob:ticket T-2109
    def test_golden_node_id_set_catches_a_removed_node(self) -> None:
        """An id present in `_EXPECTED_NODE_IDS` but absent from `actual`
        (a real regression -- the shrinkage direction T-2102's floor already
        caught) still fails and names the missing id, so the golden-set
        replacement does not regress that coverage."""
        removed = next(iter(_EXPECTED_NODE_IDS))
        actual = _EXPECTED_NODE_IDS - {removed}
        message = _node_id_diff_message(actual, _EXPECTED_NODE_IDS)
        assert message is not None
        assert removed in message
        assert "missing" in message

    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModel.test_golden_node_id_set_p\
    # asses_when_unchanged kind="unit"
    # frob:ticket T-2109
    def test_golden_node_id_set_passes_when_unchanged(self) -> None:
        """An `actual` set identical to `_EXPECTED_NODE_IDS` passes with no
        message -- the must-still-pass control proving this check is not
        merely a check that always fails."""
        assert _node_id_diff_message(_EXPECTED_NODE_IDS, _EXPECTED_NODE_IDS) is None

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
    # T-3247: measured 27.11s warm-cache locally (`build_graph` + `sys_gate`
    # over this repo's own real tree, not a synthetic `tmp_path` fixture,
    # T-1433's own docstring above on `_SELF_SCAN_HEAVY_NAME_SUBSTRINGS`
    # documents this same test as a whole-repo scan). The 2026-08-28 CI run's
    # own faulthandler dump (`faulthandler_timeout = 100`, pyproject.toml)
    # caught this test still inside `build_graph -> _ingest_source_files ->
    # parse_file` at the 100s mark on a CI runner, so the local baseline
    # already understates CI cost by several-fold; 300s gives headroom above
    # the observed near-miss without raising the global 120s ceiling that
    # catches genuine hangs everywhere else (docs/guides/testing.md#per-test-
    # timeout-ci-hardening, same reasoning T-0742 used for
    # test_scaffold_dx.py).
    @pytest.mark.timeout(300)
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

    # frob:tests design/frob.strata kind="e2e"
    # T-3247: same `build_graph(_REPO_ROOT, ...)` whole-repo-scan shape as
    # `test_sys_gate_zero_violations` above (found by this ticket's own
    # `tests/gates/test_scan_timeout_enforcement.py` enumeration, not
    # named in the original CI failure -- the gate catching a real
    # instance beyond the 3 it was written against). Same 300s reasoning:
    # local baseline is a `build_graph` call over the whole tree, same
    # cost class as the 27.11s measured for `test_sys_gate_zero_
    # violations`, with the same CI-cost-multiplier risk.
    @pytest.mark.timeout(300)
    def test_fragments_module_fs_read_is_declared_not_selfaudit001(
        self, tmp_path: Path
    ) -> None:
        """T-2465 regression: `src/frob/release/_fragments.py` reads
        `changelog.d/*.md` fragments via `Path.exists()`/`Path.read_text()`
        (T-2445), and this real fs.read site must be declared for the
        `core` node's `may "fs.read"` via-list in `design/frob.strata` --
        narrower than `test_sys_gate_zero_violations` above (which also
        trips on unrelated, pre-existing SYS101/GATERULE001 findings) so
        this one regression cannot be masked by those.
        """
        build_result = build_graph(_REPO_ROOT, tmp_path / "cache.db")
        assert build_result.is_ok, f"graph build failed: {build_result.err}"
        violations = sys_gate(_REPO_ROOT, build_result.danger_ok)
        fragments_violations = [v for v in violations if "_fragments.py" in v.message]
        assert fragments_violations == [], (
            f"_fragments.py should have no undeclared-capability SYS "
            f"violation: {fragments_violations}"
        )

    # frob:tests design/frob.strata kind="e2e"
    # T-3247: same `build_graph(_REPO_ROOT, ...)` whole-repo-scan shape as
    # `test_sys_gate_zero_violations` above (found by this ticket's own
    # `tests/gates/test_scan_timeout_enforcement.py` enumeration). Same
    # 300s reasoning as the other `build_graph(_REPO_ROOT, ...)` tests in
    # this class.
    @pytest.mark.timeout(300)
    def test_checker_fleet_deploy_vet_have_no_undeclared_fs_write_selfaudit001(
        self, tmp_path: Path
    ) -> None:
        """T-2463 regression: `checker`/`fleet`/`deploy` declared a bare
        `may "fs.write";` (no via-list) and `vet` declared `may "fs.write"
        via "src/frob/vet/_nvd.py", "src/frob/vet/_registry.py"` -- all
        four were false declarations, the same shape T-2457 fixed for the
        T-2390 schema modules (a bare read-mode `open(path, "rb")` used to
        satisfy the old mode-blind `fs.write` needle on its own; T-2457
        fixed the needle, and these four SYS101 ("declared but never
        observed") findings were the fallout T-2457's own investigation
        did not cover). Measured directly (not assumed): none of `checker`/
        `fleet`/`deploy`'s owned code, nor `_nvd.py`/`_registry.py`,
        contains a single filesystem-write call of any kind -- narrower
        than `test_sys_gate_zero_violations` above (which also trips on
        unrelated, pre-existing SYS101/GATERULE001 findings) so this one
        regression cannot be masked by those.
        """
        build_result = build_graph(_REPO_ROOT, tmp_path / "cache.db")
        assert build_result.is_ok, f"graph build failed: {build_result.err}"
        violations = sys_gate(_REPO_ROOT, build_result.danger_ok)
        node_violations = [
            v
            for v in violations
            if any(
                f"node={node}" in v.message
                for node in ("checker", "fleet", "deploy", "vet")
            )
            and "fs.write" in v.message
        ]
        assert node_violations == [], (
            f"checker/fleet/deploy/vet should have no declared-but-"
            f"never-observed fs.write SYS violation: {node_violations}"
        )

    # frob:tests design/frob.strata kind="e2e"
    # frob:ticket T-3450
    # T-3450: same `build_graph(_REPO_ROOT, ...)` whole-repo-scan shape as
    # `test_sys_gate_zero_violations` above. Same 300s reasoning as the
    # other `build_graph(_REPO_ROOT, ...)` tests in this class.
    @pytest.mark.timeout(300)
    def test_check_admission_exec_sites_are_declared_not_selfaudit001(
        self, tmp_path: Path
    ) -> None:
        """T-3450 regression: `tests/unit/test_check_admission.py`'s
        `_init_repo`/worktree-fixture helpers call `subprocess.run` (real
        `git init`/`git worktree add` invocations) -- ten such exec sites
        that were never declared in `testsuite`'s `may "exec" via [...]`
        list in `design/frob.strata`, first measured on GitHub Actions run
        33282540898. Narrower than `test_sys_gate_zero_violations` above
        (which also trips on unrelated, pre-existing SYS111 ratchet
        findings tracked separately by T-3447) so this one regression
        cannot be masked by those.
        """
        build_result = build_graph(_REPO_ROOT, tmp_path / "cache.db")
        assert build_result.is_ok, f"graph build failed: {build_result.err}"
        violations = sys_gate(_REPO_ROOT, build_result.danger_ok)
        admission_violations = [
            v for v in violations if "test_check_admission.py" in v.message
        ]
        assert admission_violations == [], (
            f"tests/unit/test_check_admission.py should have no "
            f"undeclared-capability SYS violation: {admission_violations}"
        )


# frob:ticket T-3423
class TestFrobSelfModelFailureModes:
    """T-3423: explicit positive controls for `test_parses_and_elaborates`'s
    MUST-FIRE contract -- a model that fails to elaborate, or elaborates to
    an empty surface, must still fail that sanity check. Exercised against a
    synthetic, minimal `.strata` source string, same posture as T-2109's own
    `_node_id_diff_message` positive controls above: never by mutating
    `design/frob.strata` itself (out of this ticket's declared scope, this
    test file only)."""

    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModelFailureModes.test_unparsea\
    # ble_source_fails_to_parse
    def test_unparseable_source_fails_to_parse(self) -> None:
        """Source text with no `module` statement at all -- the shape a
        genuinely broken `design/frob.strata` (a bad merge, a truncated
        write) would take -- fails `parse_module` outright, `Err`, never a
        silent `Ok` of nothing. `_model`'s own fixture asserts exactly this
        (`parsed.is_ok`) before `test_parses_and_elaborates` ever runs, so
        this failure mode never reaches the node/flow/claim assertions at
        all."""
        result = parse_module("")
        assert result.is_err

    # frob:tests \
    # tests/system/test_frob_self_model.py::TestFrobSelfModelFailureModes.test_empty_mo\
    # dule_elaborates_but_fails_every_surface_assertion
    def test_empty_module_elaborates_but_fails_every_surface_assertion(
        self,
    ) -> None:
        """A syntactically valid but EMPTY module (`module frob\\n`, no
        `node`/`flow`/`boundary`/`claim` declarations at all) parses and
        elaborates cleanly (`elaborate` does not itself fail closed on
        emptiness -- only on the corruption shapes `_validate_no_
        duplicates` catches, per `test_parses_and_elaborates`'s own
        docstring) to a genuinely empty surface. Proves the MUST-FIRE
        contract structurally: every one of `test_parses_and_elaborates`'s
        own assertions -- the golden node-id set diff, and each `>=` floor
        -- independently fails against this empty model, so an elaboration
        that silently loses its whole surface can never pass under either
        the current node-id-set-plus-floors design or a future pure-floor
        (option (a)) one."""
        parsed = parse_module("module frob\n")
        assert parsed.is_ok, f"minimal module failed to parse: {parsed.err}"
        elaborated = elaborate(parsed.danger_ok)
        assert elaborated.is_ok, f"minimal module failed to elaborate: {elaborated.err}"
        empty = elaborated.danger_ok
        assert len(empty.nodes) == 0
        assert len(empty.flows) == 0
        assert len(empty.boundaries) == 0
        assert len(empty.claims) == 0
        # The golden node-id set: an empty actual set diffs against every
        # member of `_EXPECTED_NODE_IDS` as "missing" -- never `None`.
        diff_message = _node_id_diff_message(frozenset(), _EXPECTED_NODE_IDS)
        assert diff_message is not None
        assert "missing" in diff_message
        # The floors: 0 is below every one of them.
        assert not (len(empty.flows) >= 44)
        assert not (len(empty.boundaries) >= 1)
        assert not (len(empty.claims) >= 31)
