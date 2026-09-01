import os
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok

import frob.tickets._land as _land_mod
import frob.tickets._land_git_ops as _land_git_ops_mod
from frob.gitio import GitError, ProcResult
from frob.tickets import (
    Origin,
    TicketKind,
    TicketState,
    new_ticket,
    set_done_report,
    transition,
)
from frob.tickets._land import land
from frob.tickets._models import (
    DoneReportClaims,
    LandError,
    Ticket,
    render_claims_block,
)
from frob.tickets._store import (
    _serialize_ticket,
    atomic_write,
    ledger_path,
    load_all,
    write_ticket,
)
from tests.ticket_land_suite.conftest import (
    _commit_all,
    _failing_run_argv,
    _git_init,
    _install_changelog_guard_hook,
    _make_closeable,
    _run,
    _spec,
)

pytestmark = pytest.mark.heavy_subprocess



class TestClaimDivergencePostMerge:
    """T-0754: `land`'s `passed`/`check_gates` callables re-verify a
    ticket's `### Captured claims` Done-report section against the
    POST-MERGE tree, mirroring D-05's evidence re-verification but for the
    captured test-count/gate-state CLAIMS themselves.

    Review round 2: `check_gates` returns `(errors, warnings, waived)`
    ints (never the raw `frob check` summary line, whose timing blob is
    nondeterministic even against an unchanged tree -- the FATAL this
    round's fix closes), and the test-count half is derived from the SAME
    `passed()` run D-05's own evidence re-verification already made (no
    separate `run_tests` parameter at the land layer any more)."""

    def _make_closeable_with_claims(
        self,
        root: Path,
        ticket_id: str,
        *,
        test_count: int,
        gate_errors: int = 0,
        gate_warnings: int = 0,
        gate_waived: int = 0,
    ) -> None:
        """Drive `ticket_id` to closeable (`_make_closeable`) then append a
        `### Captured claims` section to its Done report, exactly the shape
        `render_claims_block` writes."""
        _make_closeable(root, ticket_id)
        loaded = load_all(root)
        ticket = loaded.danger_ok[ticket_id]
        claims_block = (
            f"### Captured claims\n"
            f"- tests: {test_count} passed (from 1 evidence id(s))\n"
            f"- gates: {gate_errors} error(s), {gate_warnings} warning(s), "
            f"{gate_waived} waived"
        )
        ticket = ticket.model_copy(
            update={"body": ticket.body + "\n" + claims_block + "\n"}
        )
        assert write_ticket(root, ticket).is_ok

    def test_matching_claims_land_succeeds(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_matching_claims_land_succeeds  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-match", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with matching captured claims"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1)
        _commit_all(wt, "advance ticket with matching captured claims")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_ok

    def test_divergent_test_count_refuses_land(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_divergent_test_count_refuses_land  # noqa: E501
        """`passed()` still reports the ticket's one real evidence id as
        PASSING (so D-05's own evidence re-verify stays green and does not
        pre-empt this with `NotCloseable`) -- but the Done report's own
        captured claim says 2 tests passed, which the real post-merge
        `passed()` run of 1 (D-05's own result, reused per review round 2
        fix #3) can never match. Isolates the `ClaimDivergence` path from
        D-05's own evidence-resolution/pass checks."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-tests", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with stale test-count claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=2)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        assert ticket.evidence == ("tests/test_x.py::test_ok",)
        _commit_all(wt, "advance ticket with stale test-count claim")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before

    def test_strictly_improved_test_count_auto_accepts_and_rewrites_recap(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_strictly_improved_test_count_auto_accepts_and_rewrites_recap  # noqa: E501
        """T-1000 (churn item 1): a captured claim of 0/0 (recorded before
        the ticket's one real evidence id existed, or a stale recap from a
        send-back cycle) against a fresh post-merge re-run showing the
        real 1/1 passing is a STRICT IMPROVEMENT, never a divergence -- the
        land succeeds (no manual `frob ticket done-report` + re-land
        cycle) and the landed ticket's recap is rewritten to the fresh
        1/1 numbers."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-improved", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with stale 0/0 captured claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        claims_block = (
            "### Captured claims\n"
            "- tests: 0 passed (from 0 evidence id(s))\n"
            "- gates: 0 error(s), 0 warning(s), 0 waived"
        )
        ticket = ticket.model_copy(
            update={"body": ticket.body + "\n" + claims_block + "\n"}
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "advance ticket with stale 0/0 captured claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_ok
        final_id = result.danger_ok.final_id
        landed = load_all(repo).danger_ok[final_id]
        assert "- tests: 1 passed (from 1 evidence id(s))" in landed.body
        assert "- tests: 0 passed (from 0 evidence id(s))" not in landed.body

    def test_divergent_gate_errors_refuses_land(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_divergent_gate_errors_refuses_land  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-claims-gates", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with stale gate-state claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1, gate_errors=0)
        _commit_all(wt, "advance ticket with stale gate-state claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (3, 0, 0),
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence

    def test_lower_gate_error_count_than_claim_still_lands(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_lower_gate_error_count_than_claim_still_lands  # noqa: E501
        """T-0846: a fresh post-merge error count LOWER than the captured
        claim (a sibling land fixed something on main between done-report
        time and this post-merge check, or a scoped-run WAIVE004 finding
        stopped counting) must not refuse the land -- only an INCREASE is
        the actionable signal. This fails against the pre-T-0846 strict
        `!=` comparison (3 != 0 also refused a strict decrease) and passes
        against the fixed `>` comparison."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-gate-decrease", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket with an improved gate-state claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1, gate_errors=3)
        _commit_all(wt, "advance ticket with an improved gate-state claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # Recorded claim was 3 error(s); the fresh post-merge check
            # now shows 0 -- an improvement, not a divergence.
            check_gates=lambda: (0, 0, 0),
        )

        assert result.is_ok

    # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity  # noqa: E501
    def test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity(
        self, repo: Path
    ) -> None:
        """T-0846 reviewer reject #1: a count-only comparison lets a land
        whose own diff introduces a NEW error sail through whenever an
        UNRELATED fix on the same branch removed MORE errors than that --
        the net total goes DOWN even though this land's own scope now has a
        genuinely new problem. Captured claim: 2 errors, with identities
        {RULE_A@src/other.py, RULE_B@src/other.py}. Fresh post-merge: 1
        error total (net LOWER, so the count-only `>` fallback alone would
        pass this land) but the ONE surviving finding is a brand-new
        RULE_C@src/feature.py -- inside THIS ticket's own declared scope
        (`src/**`) and absent from the captured claim. This must REFUSE via
        the identity-based comparison even though the raw count went down;
        it fails against a count-only `>` check (1 > 2 is False, would
        pass) and passes only when the identity/scope comparison is wired."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-masked", str(wt)],
            repo,
        )

        created = new_ticket(
            wt, _spec("Ticket whose own scope covers src/**", scope=("src/**",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        claims = DoneReportClaims(
            test_count=1,
            evidence_count=1,
            gate_errors=2,
            gate_warnings=0,
            gate_waived=0,
            error_findings=frozenset(
                {("RULE_A", "src/other.py"), ("RULE_B", "src/other.py")}
            ),
        )
        ticket = ticket.model_copy(
            update={"body": ticket.body + "\n" + render_claims_block(claims) + "\n"}
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "advance ticket with a to-be-masked gate-state claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # Scope-wide total DROPPED (2 -> 1) -- the count-only fallback
            # would pass this. But the one surviving finding is a NEW
            # identity, in a file this ticket's own scope covers.
            check_gates=lambda: (1, 0, 0),
            check_gate_findings=lambda: frozenset({("RULE_C", "src/feature.py")}),
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence

    def test_divergent_warning_or_waived_count_alone_still_lands(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_divergent_warning_or_waived_count_alone_still_lands  # noqa: E501
        """Review round 2 fix #1: a warning/waived-count drift ALONE (errors
        unchanged) must never refuse a land -- repo-global warning counts
        legitimately move on a busy shared branch for reasons unrelated to
        this ticket's own work."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-warn-drift", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket with warning-count drift only"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(
            wt, tid, test_count=1, gate_errors=0, gate_warnings=5, gate_waived=2
        )
        _commit_all(wt, "advance ticket with warning-count drift only")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # errors still 0 (matches the claim); warnings/waived drifted.
            check_gates=lambda: (0, 41, 9),
        )

        assert result.is_ok

    def test_no_claims_section_skips_reverification(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_no_claims_section_skips_reverification  # noqa: E501
        """A Done report predating T-0754 (no `### Captured claims`
        section) lands normally even with `passed`/`check_gates`
        supplied -- there is nothing recorded to diverge from."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-no-claims", str(wt)], repo)

        created = new_ticket(wt, _spec("Ticket with no captured claims"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with no captured claims")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=lambda: (99, 99, 99),
        )

        assert result.is_ok

    def test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds  # noqa: E501
        """T-0832: when the post-merge `check_gates()` callable cannot
        produce a gate-summary (e.g. the ticket lost its lease -- the real
        T-0830 incident), land must not compare a sentinel; it must skip
        the gate-state half of the claim comparison with an explicit
        logged notice and still land (the test-count half remains real and
        matching). No negative count appears anywhere in the notice."""
        import logging

        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-unmeasurable", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket whose fresh check cannot run"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_claims(wt, tid, test_count=1, gate_errors=0)
        _commit_all(wt, "advance ticket with a recorded but now-unmeasurable claim")

        with caplog.at_level(logging.WARNING):
            result = land(
                repo,
                tid,
                wt,
                dry_run=False,
                passed=lambda ids: frozenset(ids),
                # T-0832: simulates the fresh post-merge check finding no
                # parsable gate-summary (no lease, a crash, ...).
                check_gates=lambda: None,
            )

        assert result.is_ok
        notices = [
            r.getMessage()
            for r in caplog.records
            if "skipping gate-state re-verification" in r.getMessage()
        ]
        assert notices, "expected an explicit skip notice, got none"
        # T-1635: the notice embeds `tid` (a randomly-minted `T-draft-
        # <hex>` id, `mint_draft_id`) verbatim, twice -- a bare `"-1" not
        # in notices[0]` check intermittently failed (~1/16 of runs,
        # independent of any load/scheduling) whenever that random hex
        # happened to start with "1" right after "draft-", producing the
        # substring "...draft-1..." and tripping the sentinel check on
        # pure coincidence, not a real `-1` sentinel leak. Strip the
        # ticket id out before checking so the assertion only ever
        # catches a genuine `-1` in the FORMATTED numbers this message is
        # actually guarding against.
        assert "-1" not in notices[0].replace(tid, "<TID>")

    def test_two_unmeasured_gate_claims_never_vacuously_match(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match  # noqa: E501
        """T-0832 regression: the T-0830 incident was NOT merely that land
        printed a nonsense message -- it was that a done-report capture
        that recorded an unmeasured claim (formerly `-1`) and a land-time
        fresh check that ALSO could not measure (formerly `-1`) compared
        as vacuously EQUAL, silently passing a re-verification that
        actually verified nothing. Reproduce both halves unmeasured (via
        the real `set_done_report` capture path, not a hand-built claims
        block) and assert the gate-state comparison is skipped -- not
        silently "passed" as equal -- while the land still succeeds
        because the skip is explicit, not a false positive masquerading as
        one."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-claims-both-unmeasured", str(wt)],
            repo,
        )

        created = new_ticket(wt, _spec("Ticket with a fully unmeasured claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Capture the Done report through the REAL `set_done_report` path
        # with a `check_gates` that cannot measure -- exactly what
        # `_check_gates_summary_fn` returns for a lease-less/crashed check
        # (T-0832: `None`, never `-1`).
        done = set_done_report(
            wt,
            tid,
            why="claims captured while gate state was unmeasurable",
            run_tests=lambda ids: len(ids),
            check_gates=lambda: None,
        )
        assert done.is_ok, done.err
        assert "### Captured claims" in done.danger_ok.body
        assert "unmeasured" in done.danger_ok.body
        # T-1635: same defensive strip as the sibling test above -- `tid`
        # is a randomly-minted `T-draft-<hex>` id that can coincidentally
        # embed the substring "-1"; excluding it keeps this assertion
        # honest about what it actually guards (no `-1` sentinel in a
        # FORMATTED number, not "the random id happens to avoid one").
        assert "-1" not in done.danger_ok.body.replace(tid, "<TID>")
        _commit_all(wt, "advance ticket with a fully unmeasured captured claim")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            # Land's own fresh post-merge check ALSO cannot measure.
            check_gates=lambda: None,
        )

        # The land succeeds -- but via the explicit "nothing recorded to
        # compare" skip (claims.gate_errors is None), never via a -1 == -1
        # false-positive comparison, which is no longer representable at
        # all now that the sentinel does not exist.
        assert result.is_ok


# frob:ticket T-2913
class TestSkipInlineClaimsReverifyUnderRapid:
    """T-2913: under rapid profile, `land()` must skip its own inline
    `check_gates`/`check_gate_findings` spawn (the 144-209s cost this
    ticket measured and removed from the land critical path) -- and must
    NOT skip it under any other profile, since the deferred post-land
    sweep this relies on to still catch a regression is itself a
    rapid-only relaxation (`_land_core_invoke`/`_land_post_merge_verify`,
    `src/frob/app/ticket_runner/_land_cmd.py`)."""

    def _make_closeable_with_divergent_claim(self, root: Path, ticket_id: str) -> None:
        """Same shape as `TestClaimDivergencePostMerge._make_closeable_
        with_claims`: a Done report claiming 0 gate errors, so a fresh
        `check_gates` reporting a HIGHER count would normally refuse the
        land (`ClaimDivergence`) -- the exact signal this test class uses
        to prove whether `check_gates` was actually invoked at all."""
        _make_closeable(root, ticket_id)
        loaded = load_all(root)
        ticket = loaded.danger_ok[ticket_id]
        claims_block = (
            "### Captured claims\n"
            "- tests: 1 passed (from 1 evidence id(s))\n"
            "- gates: 0 error(s), 0 warning(s), 0 waived"
        )
        ticket = ticket.model_copy(
            update={"body": ticket.body + "\n" + claims_block + "\n"}
        )
        assert write_ticket(root, ticket).is_ok

    def test_rapid_profile_skips_inline_check_gates_spawn(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipInlineClaimsReverifyUnderRapid.test_rapid_profile_skips_inline_check_gates_spawn  # noqa: E501
        """must-be-faster / must-still-catch, rapid side: a divergent
        `check_gates` result (which `TestClaimDivergencePostMerge.
        test_divergent_gate_errors_refuses_land` proves refuses the land
        under the default profile) is never even CALLED under rapid, and
        the land succeeds despite the divergence -- because rapid defers
        that verification to the post-land sweep instead of paying for it
        inline. This is the actual time savings T-2913 measured: the spawn
        this counter stands in for is the 144-209s cost, never invoked."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-rapid-skip", str(wt)], repo)
        (wt / "frob.toml").write_text(
            '[profile]\nprofile = "rapid"\noverride_ratchet = true\n'
        )

        created = new_ticket(wt, _spec("Rapid ticket with a divergent gate claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_divergent_claim(wt, tid)
        _commit_all(wt, "advance rapid ticket with a divergent gate claim")

        calls = []

        def _spy_check_gates() -> tuple[int, int | None, int | None]:
            calls.append(1)
            return (3, 0, 0)

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=_spy_check_gates,
        )

        assert result.is_ok
        assert calls == []

    def test_non_rapid_profile_still_runs_inline_check_gates_spawn(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipInlineClaimsReverifyUnderRapid.test_non_rapid_profile_still_runs_inline_check_gates_spawn  # noqa: E501
        """must-still-catch, non-rapid side: the SAME divergent claim,
        the SAME spy, no `frob.toml` (default = standard profile) --
        `check_gates` IS called and the land refuses, exactly as
        `TestClaimDivergencePostMerge.test_divergent_gate_errors_refuses_
        land` already established. Proves T-2913's change is profile-
        gated, not a blanket skip."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-standard-no-skip", str(wt)], repo
        )

        created = new_ticket(wt, _spec("Standard ticket with a divergent gate claim"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_divergent_claim(wt, tid)
        _commit_all(wt, "advance standard ticket with a divergent gate claim")

        calls = []

        def _spy_check_gates() -> tuple[int, int | None, int | None]:
            calls.append(1)
            return (3, 0, 0)

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=_spy_check_gates,
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence
        assert calls == [1]

    def test_unreadable_profile_config_fails_closed_and_still_runs_spawn(
        self, repo: Path
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipInlineClaimsReverifyUnderRapid.test_unreadable_profile_config_fails_closed_and_still_runs_spawn  # noqa: E501
        """Fail-closed side: a malformed `frob.toml` makes `effective_
        profile` return `Err`, which `_land_should_skip_inline_claims_
        reverify` must treat as NOT-rapid (never skip) -- a broken
        config can only make a land MORE thorough, never less. Same
        divergent-claim/spy setup as the two tests above; this one
        proves the `resolved.is_err` branch specifically, which the
        rapid/non-rapid pair above never exercises (both always resolve
        `Ok`)."""
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-unreadable-profile", str(wt)],
            repo,
        )
        (wt / "frob.toml").write_text("[profile\nthis is not valid toml\n")

        created = new_ticket(wt, _spec("Ticket with an unreadable profile config"))
        assert created.is_ok
        tid = created.danger_ok.id
        self._make_closeable_with_divergent_claim(wt, tid)
        _commit_all(wt, "advance ticket with an unreadable profile config")

        calls = []

        def _spy_check_gates() -> tuple[int, int | None, int | None]:
            calls.append(1)
            return (3, 0, 0)

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            passed=lambda ids: frozenset(ids),
            check_gates=_spy_check_gates,
        )

        assert result.is_err
        assert result.danger_err == LandError.ClaimDivergence
        assert calls == [1]



# frob:ticket T-3054
class TestSkipInlineClaimsReverifyUnderDeclaredDeadline:
    """T-3054: `_land_should_skip_inline_claims_reverify` also skips the
    inline `check_gates`/`check_gate_findings` spawn -- regardless of
    profile -- when a declared `FROB_LAND_DEADLINE_S` cannot plausibly
    cover its estimated cost, converting the SIGKILL-mid-spawn worst case
    into a clean skip (same posture T-2913 already established for rapid
    profile, extended here by the SAME `FROB_LAND_DEADLINE_S`/estimator
    T-2774 already uses for the land-lock wait)."""

    # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline.test_insufficient_deadline_skips_regardless_of_profile  # noqa: E501
    def test_insufficient_deadline_skips_regardless_of_profile(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-FIRE (the ticket's own subject): a declared deadline too
        small to cover the estimated inline spawn cost skips it even
        under the DEFAULT (non-rapid) profile, where T-2913's own rapid
        gate would never have skipped it."""
        from frob.tickets._land import _land_should_skip_inline_claims_reverify

        worktree = tmp_path / "wt"
        worktree.mkdir()
        # No frob.toml -- default/standard profile, T-2913's own rapid
        # gate alone would return False here.
        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "1")

        assert _land_should_skip_inline_claims_reverify(worktree) is True

    # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline.test_ample_deadline_still_runs_the_spawn  # noqa: E501
    def test_ample_deadline_still_runs_the_spawn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STAY-QUIET: a generous declared deadline (comfortably
        above the estimated cost) must NOT skip the spawn under the
        default profile -- opting into a deadline is not itself a reason
        to skip verification, only a genuinely insufficient one is."""
        from frob.tickets._land import _land_should_skip_inline_claims_reverify

        worktree = tmp_path / "wt"
        worktree.mkdir()
        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "100000")

        assert _land_should_skip_inline_claims_reverify(worktree) is False

    # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline.test_no_declared_deadline_is_unchanged  # noqa: E501
    def test_no_declared_deadline_is_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """MUST-STAY-QUIET (non-regression): no `FROB_LAND_DEADLINE_S` at
        all -- every caller before T-3054 -- must behave byte-for-byte as
        before: default profile never skips."""
        from frob.tickets._land import _land_should_skip_inline_claims_reverify

        worktree = tmp_path / "wt"
        worktree.mkdir()
        monkeypatch.delenv("FROB_LAND_DEADLINE_S", raising=False)

        assert _land_should_skip_inline_claims_reverify(worktree) is False

    # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipInlineClaimsReverifyUnderDeclaredDeadline.test_unparseable_deadline_is_unchanged  # noqa: E501
    def test_unparseable_deadline_is_unchanged(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-numeric `FROB_LAND_DEADLINE_S` is ignored (logged,
        never raised) -- same degrade-quietly posture T-2774's own
        `_resolve_land_lock_wait_budget_s` already uses for the
        identical malformed-value case."""
        from frob.tickets._land import _land_should_skip_inline_claims_reverify

        worktree = tmp_path / "wt"
        worktree.mkdir()
        monkeypatch.setenv("FROB_LAND_DEADLINE_S", "not-a-number")

        assert _land_should_skip_inline_claims_reverify(worktree) is False


class TestDoneReportThenLandRealClosuresEndToEnd:
    """T-0754 review round 2 fix #2: exercises the REAL production
    closures (`_run_tests_count_fn`/`_check_gates_summary_fn`/
    `_land_passed_fn`/`_land_collected_fn` -- the exact ones `frob ticket
    done-report`/`frob ticket land` wire in, no fakes) through a full
    done-report -> land cycle against an IDENTICAL fixture-repo tree.

    This is the test that would have caught the FATAL immediately: the
    pre-review-round-2 `_check_gates_summary_fn` captured the raw `frob
    check` summary LINE, timing blob included, which differs on every
    single invocation even against a completely unchanged tree -- so
    land's strict-equality re-verification refused EVERY land, including
    this ticket's own. Every other T-0754 test (`TestClaimDivergencePostMerge`
    above, `tests/test_ticket_done_report_claims.py`) uses fake
    `passed=lambda ids: ...`/`check_gates=lambda: ...` callables, which
    cannot see this class of bug at all -- only a real subprocess spawn,
    run twice, can."""

    def test_real_closures_done_report_then_land_succeeds(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_report_then_land_succeeds  # noqa: E501
        from frob.app.ticket_runner import (
            _check_gates_summary_fn,
            _land_collected_fn,
            _land_passed_fn,
            _run_tests_count_fn,
        )
        from frob.gates import sweep_ticket

        # A deliberately tiny fixture repo -- one real, fast, passing
        # pytest test -- so the two real `frob check` spawns below (one at
        # done-report time, one at land time) stay cheap.
        main_repo = tmp_path / "main"
        _git_init(main_repo)
        atomic_write(ledger_path(main_repo), "# Tickets\n\n")
        tests_dir = main_repo / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_sample.py").write_text("def test_ok():\n    assert True\n")
        _commit_all(main_repo, "init")

        wt = tmp_path / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-e2e-real-closures", str(wt)],
            main_repo,
        )

        created = new_ticket(wt, _spec("e2e real closures"))
        assert created.is_ok
        tid = created.danger_ok.id

        assert transition(wt, tid, TicketState.PLANNED).is_ok
        # T-0473: entering IN_PROGRESS records the cross-worktree lease
        # `frob check --ticket <id>` requires to run at all (otherwise it
        # refuses with "no recorded lease ... run: frob ticket start",
        # matching real `frob ticket start`'s own side effect).
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok

        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={"evidence": ("tests/test_sample.py::test_ok",)}
        )
        assert write_ticket(wt, ticket).is_ok

        # Record an initial pre-work sweep synchronously (real `frob
        # ticket start` does this via a background spawn -- inlined here
        # for test determinism) so PRE001 does not fire on the real
        # `frob check --ticket` spawns below.
        swept = sweep_ticket(wt, ticket)
        assert swept.is_ok

        done = set_done_report(
            wt,
            tid,
            why="real e2e closures -- done-report capture",
            run_tests=_run_tests_count_fn(wt),
            check_gates=_check_gates_summary_fn(wt, tid),
        )
        assert done.is_ok, done.err
        assert "### Captured claims" in done.danger_ok.body

        _commit_all(wt, "advance e2e ticket with real captured claims")

        # THE assertion: landing this ticket through its own feature must
        # succeed -- not refuse with ClaimDivergence just because the
        # SECOND real `frob check` spawn (here) reports a different
        # per-gate timing blob than the FIRST one (above) did, against the
        # exact same tree.
        result = land(
            main_repo,
            tid,
            wt,
            dry_run=False,
            collected=_land_collected_fn(wt),
            passed=_land_passed_fn(wt),
            check_gates=_check_gates_summary_fn(wt, tid),
        )
        assert result.is_ok, result.err



class TestLandInternalEnvThroughHook:
    """T-0828: every land-internal git commit spawn (worktree wip
    snapshot, main-into-worktree merge, finalize/close, main-side
    squash-apply) must set `FROB_LAND_INTERNAL=1` in the child env or a
    scaffolded T-0731 land-owned-files `pre-commit` hook deadlocks the
    land the moment any of those commits stages CHANGELOG.md."""

    def test_land_through_changelog_guard_hook_succeeds(self, repo: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestLandInternalEnvThroughHook.test_land_through_changelog_guard_hook_succeeds  # noqa: E501
        (repo / "CHANGELOG.md").write_text("# Changelog\n")
        _commit_all(repo, "add changelog")
        _install_changelog_guard_hook(repo)

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-hook", str(wt)], repo)
        created = new_ticket(wt, _spec("Hits the hook", scope=("src/hooked.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "hooked.py").write_text("# hooked\n")
        # An uncommitted CHANGELOG.md edit gets swept into `land`'s own
        # wip-snapshot commit -- exactly the real T-0594 incident shape
        # (the wip commit, not a hand-authored one, staged the guarded
        # file and tripped the hook).
        (wt / "CHANGELOG.md").write_text("# Changelog\n\n## hooked\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.commit_sha is not None

    def test_land_internal_git_env_restores_prior_value(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_land_internal_git_env \
        # kind="unit"
        os.environ.pop("FROB_LAND_INTERNAL", None)
        with _land_git_ops_mod._land_internal_git_env():
            assert (
                os.environ.get("FROB_LAND_INTERNAL") == "1"
            )  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
        assert "FROB_LAND_INTERNAL" not in os.environ

        os.environ["FROB_LAND_INTERNAL"] = (
            "prior-value"  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
        )
        try:
            with _land_git_ops_mod._land_internal_git_env():
                assert (
                    os.environ.get("FROB_LAND_INTERNAL") == "1"
                )  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
            assert (
                os.environ.get("FROB_LAND_INTERNAL") == "prior-value"
            )  # frob:waive SEC110 reason="synthetic test-only var this test itself sets"
        finally:
            os.environ.pop("FROB_LAND_INTERNAL", None)




# frob:ticket T-2865
class TestGitFailureMessageCarriesStderr:
    """T-0828: a failed land-internal git spawn must surface its argv and
    stderr in the log line, not collapse to a bare `GitFailed`."""

    def test_describe_git_failure_includes_argv_and_stderr(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_describe_git_failure \
        # kind="unit"
        argv = ["git", "-C", "/tmp/repo", "commit", "-m", "x"]
        failed = Ok(
            ProcResult(
                argv=tuple(argv),
                returncode=1,
                stdout="",
                stderr="frob: refusing commit -- CHANGELOG.md is land-owned (T-0731)",
            )
        )
        message = _land_git_ops_mod._describe_git_failure(argv, failed)
        assert "git -C /tmp/repo commit -m x" in message
        assert "exit 1" in message
        assert "CHANGELOG.md is land-owned" in message

    def test_describe_git_failure_includes_spawn_error(self) -> None:
        # frob:tests src/frob/tickets/_land_git_ops.py::_describe_git_failure \
        # kind="unit"
        argv = ["git", "-C", "/tmp/repo", "commit", "-m", "x"]
        message = _land_git_ops_mod._describe_git_failure(argv, Err(GitError.GitFailed))
        assert "git -C /tmp/repo commit -m x" in message
        assert "spawn error" in message

    def test_wip_commit_failure_logs_stderr(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:ticket T-2865
        # frob:waive COV006 reason="T-2550 class: reached only through a public land \
        # entry point several hops out, a shape build_call_graph structurally cannot \
        # see through; confirmed reachable by direct read"
        # frob:tests src/frob/tickets/_land_git_ops.py::_do_wip_commit kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l8", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l8.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l8.py").write_text("# l8\n")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "commit" in argv,
            hard_err=False,
        )
        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        assert any("simulated failure" in r.message for r in caplog.records)




# frob:ticket T-0755
class TestMutationEvidencePrecheck:
    """T-0755: `_check_mutation_evidence` blocks a security/bug-kind
    ticket's land on an ERROR-severity TEST016 finding, but only WARNs
    (does not block) every other kind -- unit-level over the private
    helper (same posture as `TestGitFailureMessageCarriesStderr` above),
    isolating the severity-gate decision from a full land() run."""

    def _ticket(self, kind: TicketKind) -> Any:
        from datetime import date as _date


        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=kind,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            attachments=(),
            body="## Description\nx\n",
        )

    def test_security_kind_error_finding_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestMutationEvidencePrecheck.test_security_kind_error_finding_blocks  # noqa: E501
        from frob.gates._models import Severity, Violation

        ticket = self._ticket(TicketKind.SECURITY)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main")
        assert result.is_err
        assert result.danger_err == LandError.EvidenceConfirmatoryOnly

    def test_feature_kind_warn_finding_does_not_block(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestMutationEvidencePrecheck.test_feature_kind_warn_finding_does_not_block  # noqa: E501
        from frob.gates._models import Severity, Violation

        ticket = self._ticket(TicketKind.FEATURE)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.WARN,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main")
        assert result.is_ok

    def test_no_findings_is_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/ticket_land_suite/test_claim_close.py::TestMutationEvidencePrecheck.tes\
        # t_no_findings_is_ok
        ticket = self._ticket(TicketKind.SECURITY)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod, "mutation_evidence_violations", lambda *a, **k: ()
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main")
        assert result.is_ok

    def test_skip_flag_bypasses_error_finding_but_still_logs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestMutationEvidencePrecheck.test_skip_flag_bypasses_error_finding_but_still_logs  # noqa: E501
        from frob.gates._models import Severity, Violation

        ticket = self._ticket(TicketKind.SECURITY)
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        result = _land_mod._check_mutation_evidence(tmp_path, ticket, "main", skip=True)
        assert result.is_ok




# frob:ticket T-3057
class TestCheckTddOrder:
    """T-3057: `_check_tdd_order` wires TDD001 into the pre-land path,
    WARN-only -- every finding is logged, none ever refuses the land
    (deliberate, see the function's own docstring on why this is not
    promoted to blocking yet)."""

    def _ticket(self) -> Any:
        from datetime import date as _date


        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            blocked_by=(),
            parent=None,
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            attachments=(),
            body="## Description\nx\n",
        )

    def _snapshot(self) -> Any:
        from frob.graph import Digests, GraphSnapshot, SymbolId, SymbolRecord
        from frob.graph._models import Edge, EdgeKind
        from frob.lang import SymbolKind

        return GraphSnapshot(
            root="/repo",
            symbols={
                "m.py::fn": SymbolRecord(
                    id=SymbolId(path="m.py", qualname="fn"),
                    kind=SymbolKind.FUNCTION,
                    public=True,
                    digests=Digests(sig="s", body="b", doc="d"),
                    span=(1, 10),
                )
            },
            edges=(
                Edge(
                    src="m.py::fn",
                    kind=EdgeKind.TESTS,
                    target="test_m.py::test_add",
                    origin="frob:tests",
                ),
            ),
        )

    def test_logs_a_warning_for_an_implementation_first_pair_without_blocking(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: Any
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder.test_logs_a_warning_for_an_implementation_first_pair_without_blocking  # noqa: E501
        import frob.gates._tdd_order as _tdd_mod
        import frob.gitio as _gitio_mod
        import frob.graph as _graph_mod
        from frob.gates._models import Severity, Violation
        from frob.gitio import Diff, Hunk

        ticket = self._ticket()
        snapshot = self._snapshot()

        monkeypatch.setattr(
            _gitio_mod,
            "working_diff",
            lambda *a, **k: Ok(
                Diff(base="deadbeef", hunks=(Hunk(file="m.py", span=(1, 10)),))
            ),
        )
        monkeypatch.setattr(_graph_mod, "load_graph", lambda *a, **k: Ok(snapshot))
        monkeypatch.setattr(
            _tdd_mod,
            "tdd_order_violations",
            lambda *a, **k: (
                Violation(
                    rule="TDD001",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TDD001: implementation-first",
                ),
            ),
        )
        with caplog.at_level("WARNING", logger="frob.tickets._land"):
            result = _land_mod._check_tdd_order(tmp_path, ticket, "main")
        assert result.is_ok
        assert any("TDD001" in r.message for r in caplog.records)

    def test_stays_quiet_when_no_tests_edges_are_touched(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder.test_stays_quiet_when_no_tests_edges_are_touched  # noqa: E501
        import frob.gitio as _gitio_mod
        import frob.graph as _graph_mod
        from frob.gitio import Diff, Hunk

        ticket = self._ticket()
        snapshot = self._snapshot()

        monkeypatch.setattr(
            _gitio_mod,
            "working_diff",
            lambda *a, **k: Ok(
                Diff(base="deadbeef", hunks=(Hunk(file="unrelated.py", span=(1, 10)),))
            ),
        )
        monkeypatch.setattr(_graph_mod, "load_graph", lambda *a, **k: Ok(snapshot))
        result = _land_mod._check_tdd_order(tmp_path, ticket, "main")
        assert result.is_ok

    def test_never_refuses_the_land(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder.test_never_refuses_the_land  # noqa: E501
        import frob.gates._tdd_order as _tdd_mod
        import frob.gitio as _gitio_mod
        import frob.graph as _graph_mod
        from frob.gates._models import Severity, Violation
        from frob.gitio import Diff, Hunk

        ticket = self._ticket()
        snapshot = self._snapshot()

        monkeypatch.setattr(
            _gitio_mod,
            "working_diff",
            lambda *a, **k: Ok(
                Diff(base="deadbeef", hunks=(Hunk(file="m.py", span=(1, 10)),))
            ),
        )
        monkeypatch.setattr(_graph_mod, "load_graph", lambda *a, **k: Ok(snapshot))
        monkeypatch.setattr(
            _tdd_mod,
            "tdd_order_violations",
            lambda *a, **k: (
                Violation(
                    rule="TDD001",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TDD001: implementation-first, should never block",
                ),
                Violation(
                    rule="TDD001",
                    severity=Severity.UNRESOLVED,
                    file="m.py",
                    line=0,
                    message="TDD001: unresolved",
                ),
            ),
        )
        result = _land_mod._check_tdd_order(tmp_path, ticket, "main")
        assert result.is_ok

    def test_passes_the_resolved_merge_base_as_since(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-3618 (perf): `_check_tdd_order` must resolve merge-base(base_
        ref, HEAD) and thread it into `tdd_order_violations` as `since`
        -- the bound that turns each edge's git-log walk from `path`'s
        ENTIRE history into just this land's own branch range. Pinning
        the ARGUMENT `tdd_order_violations` receives (not wall-clock) is
        this ticket's own acceptance bar for a perf regression test."""
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder.test_passes_the_resolved_merge_base_as_since  # noqa: E501
        import frob.gates._tdd_order as _tdd_mod
        import frob.gitio as _gitio_mod
        import frob.graph as _graph_mod
        from frob.gitio import Diff, Hunk

        ticket = self._ticket()
        snapshot = self._snapshot()

        monkeypatch.setattr(
            _gitio_mod,
            "working_diff",
            lambda *a, **k: Ok(
                Diff(base="deadbeef", hunks=(Hunk(file="m.py", span=(1, 10)),))
            ),
        )
        monkeypatch.setattr(_graph_mod, "load_graph", lambda *a, **k: Ok(snapshot))

        received: dict[str, object] = {}

        def _spy(root: object, edges: object, *, since: object = None) -> tuple:
            received["since"] = since
            return ()

        monkeypatch.setattr(_tdd_mod, "tdd_order_violations", _spy)
        monkeypatch.setattr(
            _land_mod,
            "run_argv",
            lambda argv: Ok(
                type("Spawned", (), {"returncode": 0, "stdout": "abc123\n"})()
            ),
        )

        result = _land_mod._check_tdd_order(tmp_path, ticket, "main")
        assert result.is_ok
        assert received["since"] == "abc123"

    def test_falls_back_to_unbounded_when_merge_base_is_unresolvable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: Any
    ) -> None:
        """An unresolvable merge-base (this test's `tmp_path` is not even
        a git repo) must degrade to `since=None` -- the PRIOR unbounded
        behavior -- rather than skipping TDD001 outright, and must log
        the fallback loudly rather than silently eating the cost
        regression it re-introduces."""
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCheckTddOrder.test_falls_back_to_unbounded_when_merge_base_is_unresolvable  # noqa: E501
        import frob.gates._tdd_order as _tdd_mod
        import frob.gitio as _gitio_mod
        import frob.graph as _graph_mod
        from frob.gitio import Diff, Hunk

        ticket = self._ticket()
        snapshot = self._snapshot()

        monkeypatch.setattr(
            _gitio_mod,
            "working_diff",
            lambda *a, **k: Ok(
                Diff(base="deadbeef", hunks=(Hunk(file="m.py", span=(1, 10)),))
            ),
        )
        monkeypatch.setattr(_graph_mod, "load_graph", lambda *a, **k: Ok(snapshot))

        received: dict[str, object] = {}

        def _spy(root: object, edges: object, *, since: object = None) -> tuple:
            received["since"] = since
            return ()

        monkeypatch.setattr(_tdd_mod, "tdd_order_violations", _spy)

        with caplog.at_level("WARNING", logger="frob.tickets._land"):
            result = _land_mod._check_tdd_order(tmp_path, ticket, "main")
        assert result.is_ok
        assert received["since"] is None
        assert any("merge-base" in r.message for r in caplog.records)




# frob:ticket T-0854
class TestLiveTrackerCitationPrecheck:
    """T-0854: `_check_live_tracker_citations` blocks land when a registry
    disposition or waiver still cites the landing ticket as its live
    tracker -- unit-level over the private helper (same posture as
    `TestMutationEvidencePrecheck` above), isolating the refusal decision
    from a full land() run."""

    def _ticket_t0900(self) -> Any:

        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=date(2026, 1, 1),
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            body="## Description\nx\n",
        )

    def test_citations_found_blocks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestLiveTrackerCitationPrecheck.test_citations_found_blocks  # noqa: E501
        # T-1853: the check now only fires for a land moving the ticket to
        # a TERMINAL state (an in-progress land threatens no citation --
        # see TestLandCheckSkipsNonTerminalAnchor in
        # tests/test_tickets_live_tracker.py) -- use DONE here so this
        # test keeps exercising the still-blocking case.
        import frob.tickets._live_tracker as _live_tracker_mod

        monkeypatch.setattr(
            _live_tracker_mod,
            "live_tracker_citations",
            lambda *a, **k: ("docs/design/registry/patterns.yaml:3: deferred:T-0900",),
        )
        ticket = self._ticket_t0900().model_copy(update={"state": TicketState.DONE})
        result = _land_mod._check_live_tracker_citations(tmp_path, ticket, "main")
        assert result.is_err
        assert result.danger_err == LandError.LiveTrackerCited

    def test_no_citations_is_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestLiveTrackerCitationPrecheck.test_no_citations_is_ok  # noqa: E501
        import frob.tickets._live_tracker as _live_tracker_mod

        monkeypatch.setattr(
            _live_tracker_mod, "live_tracker_citations", lambda *a, **k: ()
        )
        result = _land_mod._check_live_tracker_citations(
            tmp_path, self._ticket_t0900(), "main"
        )
        assert result.is_ok


# frob:ticket T-0755
class TestSkipMutationEvidenceCliWiring:
    """T-0755 reviewer round 2 finding 4: `frob ticket land
    --skip-mutation-evidence` must actually parse and reach `AppConfig`,
    and default to `False` when omitted -- the exact boolean default this
    ticket's own self-check (`test_self_check_t0755_own_diff_zero_error_
    findings`) caught as an UNTESTED mutant on first landing this flag."""

    def test_flag_parses_to_true(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipMutationEvidenceCliWiring.test_flag_parses_to_true  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--skip-mutation-evidence",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_skip_mutation_evidence is True

    def test_flag_omitted_defaults_false(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestSkipMutationEvidenceCliWiring.test_flag_omitted_defaults_false  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "land",
                "T-0001",
                "--worktree",
                str(tmp_path),
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_skip_mutation_evidence is False


# frob:ticket T-0844
class TestCloseSkipMutationEvidenceCliWiring:
    """T-0844 rework (reviewer REJECT): the close-path twin of
    `TestSkipMutationEvidenceCliWiring` above -- `frob ticket close
    --skip-mutation-evidence` must actually parse and reach `AppConfig`,
    and default to `False` when omitted, the exact boolean-default shape
    T-0755's own self-check test flagged as an untested mutant on
    `ticket_skip_mutation_evidence` the first time that flag landed. This
    is the same untested-default hole T-0844 originally left open on its
    OWN new `ticket_close_skip_mutation_evidence` field."""

    def test_flag_parses_to_true(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseSkipMutationEvidenceCliWiring.test_flag_parses_to_true  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "close",
                "T-0001",
                "--skip-mutation-evidence",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_close_skip_mutation_evidence is True

    def test_flag_omitted_defaults_false(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseSkipMutationEvidenceCliWiring.test_flag_omitted_defaults_false  # noqa: E501
        from frob.__main__ import _build_parser
        from frob.app.config import AppConfig

        parser = _build_parser()
        args = parser.parse_args(["ticket", "close", "T-0001", "--path", str(tmp_path)])
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_close_skip_mutation_evidence is False




# frob:ticket T-0844
class TestCloseMutationEvidenceForTicket:
    """T-0844 rework (reviewer REJECT): unit tests over
    `frob.app.ticket_runner._close_mutation_evidence_for_ticket` --
    proving the ERROR/WARN severity split and the branch-unresolvable
    ('cannot verify') case are each real, adversarially-covered behavior,
    not confirmatory-only lines T-0755's own self-check flagged."""

    def _ticket(self, kind: TicketKind = TicketKind.SECURITY) -> Any:
        from datetime import date as _date


        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=kind,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            body="## Description\nx\n",
        )

    def test_error_severity_finding_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseMutationEvidenceForTicket.test_error_severity_finding_returns_false  # noqa: E501
        from frob.gates._models import Severity, Violation

        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("x\n")
        _commit_all(tmp_path, "init")
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.ERROR,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is False

    def test_warn_only_severity_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseMutationEvidenceForTicket.test_warn_only_severity_returns_true  # noqa: E501
        from frob.gates._models import Severity, Violation

        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("x\n")
        _commit_all(tmp_path, "init")
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod,
            "mutation_evidence_violations",
            lambda *a, **k: (
                Violation(
                    rule="TEST016",
                    severity=Severity.WARN,
                    file="m.py",
                    line=0,
                    message="TEST016: confirmatory-only",
                ),
            ),
        )
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is True

    def test_no_findings_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseMutationEvidenceForTicket.test_no_findings_returns_none  # noqa: E501
        _git_init(tmp_path)
        (tmp_path / "README.md").write_text("x\n")
        _commit_all(tmp_path, "init")
        import frob.gates as _gates_mod

        monkeypatch.setattr(
            _gates_mod, "mutation_evidence_violations", lambda *a, **k: ()
        )
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is None

    def test_unresolvable_branch_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseMutationEvidenceForTicket.test_unresolvable_branch_returns_none  # noqa: E501
        # tmp_path is NOT a git work tree -- current_branch(root) must
        # fail, and the whole check degrades to "skip", never a false
        # ERROR/OK verdict.
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is None




# frob:ticket T-0417
class TestReverifyEvidenceForClose:
    """N-02 (docs/audits/tickets-testing-round2.md): unit tests over
    `frob.app.ticket_runner._reverify_evidence_for_close` -- proving the
    still-passes/no-longer-passes/no-evidence/collection-failed branches
    are each real, adversarially-covered behavior."""

    def _ticket(self) -> Any:
        from datetime import date as _date


        return Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.FEATURE,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            scope=("m.py",),
            evidence=("test_m.py::test_add",),
            body="## Description\nx\n",
        )

    def test_no_non_cmd_evidence_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestReverifyEvidenceForClose.test_no_non_cmd_evidence_returns_none  # noqa: E501
        from datetime import date as _date

        from frob.app import ticket_runner

        ticket = Ticket(
            id="T-0900",
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.DOCS,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            evidence=("cmd:true exit=0 sha256=abcdef012345",),
            body="## Description\nx\n",
        )
        result = ticket_runner._reverify_evidence_for_close(tmp_path, ticket)
        assert result is None

    def test_collection_failure_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestReverifyEvidenceForClose.test_collection_failure_returns_false  # noqa: E501
        from frob.app import ticket_runner

        monkeypatch.setattr(
            ticket_runner,
            "_collect_python_and_rust_ids",
            lambda root: Err("boom"),
        )
        result = ticket_runner._reverify_evidence_for_close(tmp_path, self._ticket())
        assert result is False

    def test_still_passing_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestReverifyEvidenceForClose.test_still_passing_returns_true  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.ticket_runner._verify import VerifyOutcome, VerifyStatus

        monkeypatch.setattr(
            ticket_runner,
            "_collect_python_and_rust_ids",
            lambda root: Ok((frozenset({"test_m.py::test_add"}), frozenset(), {})),
        )
        monkeypatch.setattr(
            ticket_runner,
            "_verify_ids_passing",
            lambda root, ids, py, rs, runners: {
                i: VerifyOutcome(status=VerifyStatus.PASSED) for i in ids
            },
        )
        result = ticket_runner._reverify_evidence_for_close(tmp_path, self._ticket())
        assert result is True

    # frob:ticket T-2569
    def test_no_longer_passing_returns_false(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestReverifyEvidenceForClose.test_no_longer_passing_returns_false  # noqa: E501
        """Positive control (a), T-2569: a GENUINELY failing evidence node
        must still report as failing -- this is the guard against the fix
        for T-2569 accidentally disabling failure detection altogether
        while chasing down the false-positive (spawn failure) case below."""
        from frob.app import ticket_runner
        from frob.app.ticket_runner._verify import VerifyOutcome, VerifyStatus

        monkeypatch.setattr(
            ticket_runner,
            "_collect_python_and_rust_ids",
            lambda root: Ok((frozenset({"test_m.py::test_add"}), frozenset(), {})),
        )
        monkeypatch.setattr(
            ticket_runner,
            "_verify_ids_passing",
            lambda root, ids, py, rs, runners: {
                i: VerifyOutcome(status=VerifyStatus.FAILED, reason="run FAILED")
                for i in ids
            },
        )
        with caplog.at_level("WARNING"):
            result = ticket_runner._reverify_evidence_for_close(
                tmp_path, self._ticket()
            )
        assert result is False
        assert "evidence no longer passes when re-run" in caplog.text
        assert "could not be measured" not in caplog.text

    # frob:ticket T-2569
    def test_unmeasured_returns_false_with_distinct_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestReverifyEvidenceForClose.test_unmeasured_returns_false_with_distinct_message  # noqa: E501
        """Positive control (b), T-2569: a spawn failure (the real
        incident: `TestingError.SpawnFailed` under machine contention, load
        48.5 on 12 cores) must report as UNMEASURED and refuse the close --
        but with a message that says "could not measure", NEVER the
        "evidence no longer passes when re-run" wording that (before this
        fix) misreported the exact same shape as a genuine test failure."""
        from frob.app import ticket_runner
        from frob.app.ticket_runner._verify import VerifyOutcome, VerifyStatus

        monkeypatch.setattr(
            ticket_runner,
            "_collect_python_and_rust_ids",
            lambda root: Ok((frozenset({"test_m.py::test_add"}), frozenset(), {})),
        )
        monkeypatch.setattr(
            ticket_runner,
            "_verify_ids_passing",
            lambda root, ids, py, rs, runners: {
                i: VerifyOutcome(
                    status=VerifyStatus.UNMEASURED,
                    reason="could not execute (SpawnFailed)",
                )
                for i in ids
            },
        )
        with caplog.at_level("WARNING"):
            result = ticket_runner._reverify_evidence_for_close(
                tmp_path, self._ticket()
            )
        assert result is False
        assert "could not be measured" in caplog.text
        assert "evidence no longer passes when re-run" not in caplog.text


# frob:ticket T-0844
class TestCloseFailureHintMutationEvidence:
    """T-0844 rework (reviewer REJECT): `_close_failure_hint`'s
    `EvidenceConfirmatoryOnly` branch is real, dedicated behavior (names
    the skip-flag remedy), not indistinguishable from the generic
    fallback message -- the exact `compare Eq swapped` mutant T-0755's
    self-check caught as surviving."""

    def test_confirmatory_only_hint_names_skip_flag_remedy(self) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseFailureHintMutationEvidence.test_confirmatory_only_hint_names_skip_flag_remedy  # noqa: E501
        from frob.app.ticket_runner import _close_failure_hint
        from frob.tickets._models import TicketError, TicketState

        hint = _close_failure_hint(
            "T-0900", TicketState.IN_PROGRESS, TicketError.EvidenceConfirmatoryOnly
        )
        assert "--skip-mutation-evidence" in hint
        assert "TEST016" in hint

    def test_other_error_does_not_name_skip_flag_remedy(self) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseFailureHintMutationEvidence.test_other_error_does_not_name_skip_flag_remedy  # noqa: E501
        from frob.app.ticket_runner import _close_failure_hint
        from frob.tickets._models import TicketError, TicketState

        hint = _close_failure_hint(
            "T-0900", TicketState.IN_PROGRESS, TicketError.MissingEvidence
        )
        assert "--skip-mutation-evidence" not in hint




# frob:ticket T-0844
class TestCloseSkipMutationEvidenceBypass:
    """T-0844 rework (reviewer REJECT): `_close`'s
    `mutation_evidence is False and cfg.ticket_close_skip_mutation_evidence`
    guard -- both operands genuinely matter (kills `bool False negated`
    and `boolop And swapped`), exercised end to end through a real
    `frob ticket close` call rather than asserted in isolation."""

    def _write_closeable_security_ticket(
        self, root: Path, ticket_id: str = "T-0900"
    ) -> None:
        from datetime import date as _date

        from frob.tickets import Origin, Ticket, TicketKind, TicketState

        ticket = Ticket(
            id=ticket_id,
            title="sample",
            state=TicketState.IN_PROGRESS,
            kind=TicketKind.SECURITY,
            origin=Origin.HUMAN,
            created=_date(2026, 1, 1),
            evidence=("tests/test_thing.py::test_it",),
            body="## Description\nx\n\n## Done report\nDone.\n",
        )
        tickets_dir = root / "tickets"
        tickets_dir.mkdir(parents=True, exist_ok=True)
        (tickets_dir / f"{ticket_id}-sample.md").write_text(
            _serialize_ticket(ticket), encoding="utf-8"
        )

    def test_skip_flag_bypasses_error_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseSkipMutationEvidenceBypass.test_skip_flag_bypasses_error_verdict  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        self._write_closeable_security_ticket(tmp_path)
        monkeypatch.setattr(
            ticket_runner,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket, base_ref="main": False,
        )
        monkeypatch.setattr(
            ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        monkeypatch.setattr(
            ticket_runner, "_reverify_evidence_for_close", lambda root, ticket: None
        )
        cfg = AppConfig(ticket_id="T-0900", ticket_close_skip_mutation_evidence=True)
        ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.DONE

    def test_no_skip_flag_refuses_on_error_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/ticket_land_suite/test_claim_close.py::TestCloseSkipMutationEvidenceBypass.test_no_skip_flag_refuses_on_error_verdict  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        self._write_closeable_security_ticket(tmp_path)
        monkeypatch.setattr(
            ticket_runner,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket, base_ref="main": False,
        )
        monkeypatch.setattr(
            ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        monkeypatch.setattr(
            ticket_runner, "_reverify_evidence_for_close", lambda root, ticket: None
        )
        cfg = AppConfig(ticket_id="T-0900", ticket_close_skip_mutation_evidence=False)
        with pytest.raises(SystemExit):
            ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.IN_PROGRESS
