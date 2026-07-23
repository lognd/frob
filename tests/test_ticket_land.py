"""T-0176: `frob ticket land` -- one-command landing.

Fixture-repo tests reproducing the real incident classes the ticket body
names: a stale-base worktree silently deleting a feature main already
landed, a `tickets.md` both-sides-append textual conflict, and provisional
(draft) id finalization at land time. Uses real git subprocesses (matching
tests/test_tickets_collision.py's style) -- not mocks -- because the whole
point of `land` is real merge/conflict/deletion behavior.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from typani.result import Err, Ok

import frob.tickets._land as _land_mod
from frob.gates import PreworkSweep, load_prework, record_prework, scope_digest
from frob.gitio import GitError, ProcResult, run_argv
from frob.graph import build_graph
from frob.tickets import (
    Origin,
    TicketKind,
    TicketSpec,
    TicketState,
    new_ticket,
    transition,
)
from frob.tickets._land import land, splice_ledger
from frob.tickets._models import AcceptanceCriterion, LandError
from frob.tickets._store import (
    atomic_write,
    ledger_path,
    load_all,
    load_archive,
    write_ticket,
)


def _failing_run_argv(
    monkeypatch: pytest.MonkeyPatch,
    should_fail: Callable[[Sequence[str]], bool],
    *,
    hard_err: bool = False,
) -> None:
    """Patch `frob.tickets._land.run_argv` (the single import point every
    helper in the module calls through) so any invocation matching
    `should_fail` returns a git failure -- either a bad returncode
    (`hard_err=False`) or an `Err(GitError...)` result (`hard_err=True`) --
    while everything else delegates to the real `run_argv`. This is how a
    real, hard-to-reproduce git subprocess failure (permission denial, disk
    full, a corrupted ref) gets exercised deterministically."""

    def _fake(argv: Sequence[str], **kwargs: Any) -> Any:
        if should_fail(argv):
            if hard_err:
                return Err(GitError.GitFailed)
            return Ok(
                ProcResult(
                    argv=tuple(argv),
                    returncode=1,
                    stdout="",
                    stderr="simulated failure",
                )
            )
        return run_argv(argv, **kwargs)

    monkeypatch.setattr(_land_mod, "run_argv", _fake)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


def _git_init(root: Path, *, branch: str = "main") -> None:
    root.mkdir(parents=True, exist_ok=True)
    _run(["git", "init", "-q", "-b", branch], root)
    _run(["git", "config", "user.email", "test@example.com"], root)
    _run(["git", "config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> None:
    _run(["git", "add", "-A"], root)
    _run(["git", "commit", "-q", "-m", message], root)


def _status_ignoring_frob(root: Path) -> str:
    """`git status --porcelain` output for `root`, with any `.frob/` entry
    (T-0577: `land()`'s own `.frob/land.lock` serialization lock, created
    lazily and left in place like every other `.frob/` scratch artifact --
    frob-local state a real repo is expected to `.gitignore`, never a
    genuine leftover a "leaves no trace" assertion should fail on)
    filtered out."""
    raw = _run(["git", "status", "--porcelain"], root).stdout.strip()
    lines = [line for line in raw.splitlines() if ".frob/" not in line]
    return "\n".join(lines)


def _spec(title: str, *, scope: tuple[str, ...] = ()) -> TicketSpec:
    return TicketSpec(
        title=title, kind=TicketKind.FEATURE, origin=Origin.AGENT, scope=scope
    )


def _make_closeable(root: Path, ticket_id: str) -> None:
    """Drive `ticket_id` to a state `transition(..., DONE)` will accept:
    planned -> in-progress, evidence + Done report attached."""
    assert transition(root, ticket_id, TicketState.PLANNED).is_ok
    assert transition(root, ticket_id, TicketState.IN_PROGRESS).is_ok
    loaded = load_all(root)
    ticket = loaded.danger_ok[ticket_id]
    ticket = ticket.model_copy(
        update={
            "evidence": ("tests/test_x.py::test_ok",),
            "body": ticket.body + "\n## Done report\n\nevidence attached\n",
        }
    )
    assert write_ticket(root, ticket).is_ok


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A main checkout with an initialized ledger and one committed file."""
    main_repo = tmp_path / "main"
    _git_init(main_repo)
    atomic_write(ledger_path(main_repo), "# Tickets\n\n")
    (main_repo / "src").mkdir()
    (main_repo / "src" / "feature.py").write_text("# landed feature\n")
    _commit_all(main_repo, "init")
    return main_repo


class TestSpliceLedger:
    """`splice_ledger` -- the id-level merge tickets.md conflicts always go
    through, never git's line-level textual algorithm."""

    def test_disjoint_ids_both_kept(self, tmp_path: Path) -> None:
        ours = new_ticket(tmp_path, _spec("Ours"))
        assert ours.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # A second, DISJOINT id on "their" side -- write it directly rather
        # than via new_ticket (two non-git tmp dirs would both allocate
        # T-0001, which is not the scenario under test: two SIDES of an
        # already-diverged ledger, one entry each).
        theirs_path = tmp_path / "theirs"
        theirs_path.mkdir()
        theirs_ticket = ours.danger_ok.model_copy(
            update={"id": "T-0002", "title": "Theirs"}
        )
        atomic_write(ledger_path(theirs_path), "# Tickets\n\n")
        assert write_ticket(theirs_path, theirs_ticket).is_ok
        theirs_text = ledger_path(theirs_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "Ours" in spliced.danger_ok
        assert "Theirs" in spliced.danger_ok

    def test_same_id_newer_state_wins(self, tmp_path: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::splice_ledger kind="unit"
        created = new_ticket(tmp_path, _spec("Shared"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        assert "state: planned" in spliced.danger_ok
        assert "state: queued" not in spliced.danger_ok

    # frob:tests src/frob/tickets/_land.py::splice_ledger kind="unit"
    def test_malformed_ours_propagates_as_err(self, tmp_path: Path) -> None:
        """A malformed `ours_text` (a ticket marker with no ```yaml
        frontmatter) must surface `_parse_ledger`'s error unchanged --
        `splice_ledger` never silently drops the ours side."""
        malformed_ours = "# Tickets\n\n<!-- ticket:T-0001 -->\nno frontmatter here\n"

        valid = new_ticket(tmp_path, _spec("Theirs"))
        assert valid.is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(malformed_ours, theirs_text)
        assert spliced.is_err

    # frob:tests src/frob/tickets/_land.py::splice_ledger kind="unit"
    def test_malformed_theirs_propagates_as_err(self, tmp_path: Path) -> None:
        """A malformed `theirs_text` must ALSO surface as `Err` -- the
        second `_parse_ledger` call's error path is exercised
        independently of the first (both sides are fallible)."""
        valid = new_ticket(tmp_path, _spec("Ours"))
        assert valid.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        malformed_theirs = "# Tickets\n\n<!-- ticket:T-0002 -->\nno frontmatter here\n"

        spliced = splice_ledger(ours_text, malformed_theirs)
        assert spliced.is_err


class TestSpliceOnlyTicket:
    """`_splice_only_ticket` (T-0479) -- the ledger splice scoped to ONE
    ticket id, the fix for the T-0475 sibling-resurrection incident."""

    # frob:tests src/frob/tickets/_land.py::_splice_only_ticket kind="unit"
    def test_sibling_state_never_taken_from_worktree(self, tmp_path: Path) -> None:
        """Main has T-A queued (already requeued back from in-progress) and
        T-B queued. The worktree's stale copy still remembers T-A as
        in-progress. Landing T-B must not resurrect T-A's stale
        in-progress state -- only T-B's own block may come from the
        worktree."""
        created_a = new_ticket(tmp_path, _spec("Sibling A"))
        assert created_a.is_ok
        tid_a = created_a.danger_ok.id
        created_b = new_ticket(tmp_path, _spec("Sibling B"))
        assert created_b.is_ok
        tid_b = created_b.danger_ok.id

        # Worktree's stale snapshot: T-A in-progress.
        assert transition(tmp_path, tid_a, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_a, TicketState.IN_PROGRESS).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        # Main has since requeued T-A back to queued, and separately
        # progressed T-B to planned.
        assert transition(tmp_path, tid_a, TicketState.QUEUED).is_ok
        assert transition(tmp_path, tid_b, TicketState.PLANNED).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_mod._splice_only_ticket(main_text, worktree_text, tid_b)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok)
        assert parsed.is_ok
        merged = parsed.danger_ok
        assert merged[tid_a].state == TicketState.QUEUED  # sibling untouched
        assert merged[tid_b].state == TicketState.PLANNED  # landed ticket's own block

    # frob:tests src/frob/tickets/_land.py::_splice_only_ticket kind="unit"
    def test_landed_tickets_own_divergence_still_resolved(self, tmp_path: Path) -> None:
        """If the SAME ticket id genuinely diverges between main and the
        worktree, `_newer` still resolves it (via the scoped splice) --
        only sibling ids are excluded from consideration."""
        created = new_ticket(tmp_path, _spec("Landing"))
        assert created.is_ok
        tid = created.danger_ok.id
        main_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        spliced = _land_mod._splice_only_ticket(main_text, worktree_text, tid)
        assert spliced.is_ok
        assert "state: planned" in spliced.danger_ok

    # frob:tests src/frob/tickets/_land.py::splice_ledger kind="unit"
    def test_whole_ledger_splice_never_regresses_a_sibling_from_done(
        self, tmp_path: Path
    ) -> None:
        """T-0537: `splice_ledger` (the whole-ledger merge used by `frob
        ticket merge-driver`) must never let a stale non-terminal copy of
        an already-DONE ticket win, regardless of which side
        (`ours`/`theirs`) carries it -- `_newer`'s state-rank tiebreak
        (terminal ranks highest) already makes this structurally
        impossible whenever a divergence goes THROUGH the splice; this is
        the regression-lock proving it, the exact incident class a
        hand-resolved `tickets.md` conflict (bypassing the splice
        entirely) produced instead (7 closed tickets resurrected to
        queued)."""
        created = new_ticket(tmp_path, _spec("Closed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        done_ticket = loaded.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(tmp_path, done_ticket).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # theirs (a stale branch) still remembers it as queued.
        stale = done_ticket.model_copy(update={"state": TicketState.QUEUED})
        assert write_ticket(tmp_path, stale).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok)
        assert parsed.is_ok
        assert parsed.danger_ok[tid].state == TicketState.DONE


class TestSiblingDoneReportPreserved:
    """T-0577: a real multi-ticket-worktree incident -- landing T-0386 in a
    worktree that ALSO carried sibling tickets T-0387/T-0388 (in-progress,
    review-gated, each with its own substantive Done report already
    written) spliced main's bare `queued` blocks for those siblings over
    the worktree's richer copies, erasing their Done reports and
    regressing their state. `_splice_only_ticket` must keep whichever side
    carries a substantive Done report when the OTHER side has none, even
    for a sibling id it does not otherwise touch."""

    # frob:tests src/frob/tickets/_land.py::_splice_only_ticket kind="unit"
    def test_sibling_done_report_survives_landing_another_ticket(
        self, tmp_path: Path
    ) -> None:
        created_landed = new_ticket(tmp_path, _spec("Landed ticket"))
        assert created_landed.is_ok
        tid_landed = created_landed.danger_ok.id
        created_sibling = new_ticket(tmp_path, _spec("Sibling with done report"))
        assert created_sibling.is_ok
        tid_sibling = created_sibling.danger_ok.id

        # Worktree: sibling driven to in-progress with a substantive Done
        # report already written (review-gated, awaiting its OWN land).
        _make_closeable(tmp_path, tid_sibling)
        worktree_text = ledger_path(tmp_path).read_text()

        # Main: sibling is still a bare queued block (never advanced there
        # -- this worktree is the only place it has been worked).
        loaded = load_all(tmp_path).danger_ok
        bare_sibling = loaded[tid_sibling].model_copy(
            update={
                "state": TicketState.QUEUED,
                "evidence": (),
                "body": loaded[tid_sibling].body.split("## Done report")[0],
            }
        )
        merged = dict(loaded)
        merged[tid_sibling] = bare_sibling
        from frob.tickets._store import _render_ledger

        main_text = _render_ledger(merged)

        spliced = _land_mod._splice_only_ticket(main_text, worktree_text, tid_landed)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid_sibling].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid_sibling].body
        assert parsed[tid_sibling].evidence == ("tests/test_x.py::test_ok",)

    # frob:tests src/frob/tickets/_land.py::_splice_only_ticket kind="unit"
    def test_sibling_requeue_on_main_still_wins_when_neither_side_has_a_done_report(
        self, tmp_path: Path
    ) -> None:
        """The T-0479/T-0475 case must stay fixed: a sibling with NO Done
        report on either side, stale in-progress in the worktree and
        requeued on main, still resolves to main's requeued state -- the
        T-0577 preservation rule only fires when the worktree side actually
        carries a Done report main lacks, never as a blanket "worktree
        wins" rule."""
        created_landed = new_ticket(tmp_path, _spec("Landed ticket"))
        assert created_landed.is_ok
        tid_landed = created_landed.danger_ok.id
        created_sibling = new_ticket(tmp_path, _spec("Sibling requeued"))
        assert created_sibling.is_ok
        tid_sibling = created_sibling.danger_ok.id

        assert transition(tmp_path, tid_sibling, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid_sibling, TicketState.IN_PROGRESS).is_ok
        worktree_text = ledger_path(tmp_path).read_text()

        assert transition(tmp_path, tid_sibling, TicketState.QUEUED).is_ok
        main_text = ledger_path(tmp_path).read_text()

        spliced = _land_mod._splice_only_ticket(main_text, worktree_text, tid_landed)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid_sibling].state == TicketState.QUEUED


# frob:ticket T-0682
class TestSpliceLedgerRicherStatePreference:
    """T-0682: the git-merge-driver path (`splice_ledger`, invoked by the
    registered `tickets.md` merge driver for ANY `git merge`/`pull`/`rebase`
    -- not just `frob ticket land`'s own already-ticket-scoped internal
    splice) previously ranked a same-id divergence by state-rank alone,
    so a divergence where the Done-report side happened to sit at a LOWER
    state-rank than the reportless side still lost -- observed twice in the
    field landing T-0633/T-0637, where each land's merge-main-into-worktree
    stage regressed the landing ticket's own block back toward main's bare
    state (the Done report text itself survived only because it lives in
    the body, not the frontmatter `state:` field the rank comparison acted
    on).

    `_newer`'s fix is a QUALIFIED preference, not a blanket "report always
    wins": a first pass at this ticket made Done-report presence an
    unconditional override, which a reviewer caught as the INVERSE bug --
    a STALE report on a lower-rank block (e.g. a ticket requeued back down
    without its old report body ever getting stripped) would then beat a
    genuinely more-advanced, reportless side. The reported side now wins
    over a reportless one ONLY IF the reportless side does not STRICTLY
    outrank it; a strictly-higher-rank reportless side still wins. These
    tests mirror T-0577's two-direction shape, but against `splice_ledger`
    (the whole-ledger merge) directly rather than the ticket-scoped
    `_splice_only_ticket`."""

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_report_side_still_wins_when_it_also_outranks_the_reportless_side  # noqa: E501
    def test_report_side_still_wins_when_it_also_outranks_the_reportless_side(
        self, tmp_path: Path
    ) -> None:
        """The original T-0682 field incident: `ours` (the worktree side,
        in a `merge main into worktree`) is `in-progress` (rank 2) with a
        substantive Done report; `theirs` (main) is a bare `queued` (rank
        0). The reported side is ALSO the higher-rank side here, so it
        wins under both the old (buggy) and new (qualified) rule -- this
        pins the incident that motivated the fix in the first place."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(tmp_path).danger_ok[tid]
        with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, with_report).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        theirs = with_report.model_copy(
            update={
                "state": TicketState.QUEUED,
                "body": with_report.body.split("## Done report")[0],
            }
        )
        assert write_ticket(tmp_path, theirs).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side  # noqa: E501
    def test_stale_report_on_lower_rank_still_loses_to_a_strictly_outranking_reportless_side(  # noqa: E501
        self, tmp_path: Path
    ) -> None:
        """The reviewer-caught inverse case: `ours` is a bare `queued`
        (rank 0) that still carries a STALE Done report (e.g. requeued
        back down without the report ever being stripped); `theirs` is
        `in-progress` (rank 2, strictly higher) with no report at all --
        genuine further rework since. An unqualified "report always wins"
        rule would resurrect the stale queued+report block here; the
        qualification must let the strictly-outranking reportless side
        win instead."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        stale_with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, stale_with_report).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        theirs = stale_with_report.model_copy(
            update={
                "state": TicketState.IN_PROGRESS,
                "body": stale_with_report.body.split("## Done report")[0],
            }
        )
        assert write_ticket(tmp_path, theirs).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" not in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on  # noqa: E501
    def test_stale_report_on_lower_rank_still_loses_regardless_of_which_side_it_is_on(
        self, tmp_path: Path
    ) -> None:
        """Same divergence as the previous test, but with the stale report
        on `theirs` instead of `ours` -- the qualification is symmetric,
        not an accidental artifact of argument order."""
        created = new_ticket(tmp_path, _spec("Landing ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        stale_with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(tmp_path, stale_with_report).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        ours = stale_with_report.model_copy(
            update={
                "state": TicketState.IN_PROGRESS,
                "body": stale_with_report.body.split("## Done report")[0],
            }
        )
        assert write_ticket(tmp_path, ours).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" not in parsed[tid].body

    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerRicherStatePreference.test_neither_side_reporting_still_falls_back_to_state_rank  # noqa: E501
    def test_neither_side_reporting_still_falls_back_to_state_rank(
        self, tmp_path: Path
    ) -> None:
        """The T-0577/T-0537 non-regression guard stays intact: when
        NEITHER side carries a substantive Done report, the comparison
        falls back to plain state-rank exactly as before -- this is not a
        blanket "richer body always wins" rule."""
        created = new_ticket(tmp_path, _spec("Closed elsewhere"))
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]
        done_ticket = loaded.model_copy(update={"state": TicketState.DONE})
        assert write_ticket(tmp_path, done_ticket).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        stale = done_ticket.model_copy(update={"state": TicketState.QUEUED})
        assert write_ticket(tmp_path, stale).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.DONE


class TestLand:
    """`frob.tickets.land` against real fixture repos."""

    def test_dry_run_lands_cleanly_and_leaves_no_trace(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-a", str(wt)], repo)
        created = new_ticket(wt, _spec("Add widget", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "add widget")

        # Main gains a commit AFTER the worktree branched, so merging main
        # into the worktree is a real merge, not a no-op.
        (repo / "src" / "unrelated.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        before_wt_sha = _run(["git", "rev-parse", "HEAD"], wt).stdout.strip()

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.dry_run is True
        assert report.merged_main_into_worktree is True

        # Dry run must leave both checkouts exactly as found.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "rev-parse", "HEAD"], wt).stdout.strip() == before_wt_sha
        assert _status_ignoring_frob(repo) == ""
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""

    def test_real_land_lands(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-b", str(wt)], repo)
        created = new_ticket(wt, _spec("Add gadget", scope=("src/gadget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "gadget.py").write_text("# new gadget\n")
        _commit_all(wt, "add gadget")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.dry_run is False
        assert report.commit_sha is not None
        assert (repo / "src" / "gadget.py").exists()

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE

    def test_refuses_on_dirty_main(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-c", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        (repo / "dirty.txt").write_text("uncommitted\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain

    def test_refuses_without_evidence_or_done_report(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-d", str(wt)], repo)
        created = new_ticket(wt, _spec("Not ready"))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(wt, "wip")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Nothing must have been touched -- close validation runs BEFORE any
        # git mutation, so main and the worktree are exactly as found.
        assert _status_ignoring_frob(repo) == ""
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


class TestWarnIfNativeStale:
    """T-0248: `land` warns loudly (without blocking) when the just-landed
    tree's native source outpaces its own built extension -- the T-0166
    review incident class."""

    def test_real_land_logs_stale_native_warning(
        self,
        repo: Path,
        caplog: pytest.LogCaptureFixture,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_warn_if_native_stale kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native", str(wt)], repo)
        created = new_ticket(wt, _spec("Grammar change", scope=("src/grammar.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "grammar.py").write_text("# grammar change\n")
        _commit_all(wt, "grammar change")

        monkeypatch.setattr(
            "frob.strata._native_staleness.stale_native_warning",
            lambda root: "STALE NATIVE: fake grammar-ahead-of-native fixture",
        )

        with caplog.at_level("WARNING", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_ok, result.err
        assert any("STALE NATIVE" in record.message for record in caplog.records)

    def test_real_land_no_warning_when_native_fresh(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_warn_if_native_stale kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-fresh", str(wt)], repo)
        created = new_ticket(wt, _spec("Non-native change", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "other.py").write_text("# unrelated change\n")
        _commit_all(wt, "unrelated change")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert not any("STALE NATIVE" in r.message for r in caplog.records)


class TestCloseFailAfterMerge:
    """`_transition_guard` can still refuse `DONE` even after `_validate_
    closeable`'s precheck passed on the worktree's OWN snapshot -- the
    splice can overwrite the worktree's in-memory ticket with a further-
    along same-id entry from main (e.g. DROPPED, a terminal state with no
    outgoing transitions) between the precheck and the close call. `land`
    must surface `LandError.CloseFailed` and name the manual remedy rather
    than silently landing a ticket main considers dropped."""

    def test_close_fails_after_merge_when_main_dropped_same_id(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-k", str(wt)], repo)

        created = new_ticket(wt, _spec("Race with main", scope=("src/raced.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "raced.py").write_text("# raced feature\n")
        _commit_all(wt, "add raced feature")

        # Main independently ends up with the SAME ticket id, further along
        # the state machine (DROPPED, terminal) -- simulating a race where
        # main dropped this exact ticket after the worktree branched.
        atomic_write(ledger_path(repo), "# Tickets\n\n")
        dropped = created.danger_ok.model_copy(update={"state": TicketState.DROPPED})
        assert write_ticket(repo, dropped).is_ok
        _commit_all(repo, "main independently drops the same ticket id")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.CloseFailed

        # The merge into the worktree landed (that happens before close),
        # but main itself must be untouched -- the failure surfaces before
        # any squash-apply onto main.
        landed_main = load_all(repo)
        assert landed_main.is_ok
        assert landed_main.danger_ok[tid].state == TicketState.DROPPED


class TestStaleBaseDeletion:
    """Incident class 1: a worktree branched from an old main base ends up,
    relative to main's CURRENT tip, deleting a file main already landed --
    the deletion-filter check must abort loudly rather than let that
    deletion reach main."""

    def test_unowned_deletion_aborts_loudly(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-e", str(wt)], repo)

        # The worktree's own (out-of-scope) change deletes a file main has
        # -- simulating a stale-base agent that clobbered an unrelated file
        # it never should have touched.
        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Unrelated ticket", scope=("src/other.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions

        # Worktree must be left clean (merge --abort ran) -- no half-applied
        # merge state left behind by the aborted dry run.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""
        assert (repo / "src" / "feature.py").exists()

    def test_scoped_deletion_is_allowed(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-f", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Retire feature", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "retire feature.py, in scope")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err


class TestLedgerBothSidesAppend:
    """Incident class 2: main gets a new ticket appended AFTER the worktree
    branched, and the worktree independently appends its own new ticket --
    a textual same-region conflict in tickets.md that must resolve as
    "keep both", not as a real conflict requiring a human."""

    def test_both_sides_append_merges_cleanly(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-g", str(wt)], repo)

        created_wt = new_ticket(
            wt, _spec("Worktree ticket", scope=("src/wt_thing.py",))
        )
        assert created_wt.is_ok
        wt_tid = created_wt.danger_ok.id
        _make_closeable(wt, wt_tid)
        (wt / "src" / "wt_thing.py").write_text("# from worktree\n")
        _commit_all(wt, "worktree ticket + feature")

        # Main independently gains a new ticket AFTER the worktree branched.
        created_main = new_ticket(repo, _spec("Main-side ticket"))
        assert created_main.is_ok
        main_tid = created_main.danger_ok.id
        _commit_all(repo, "main-side ticket")

        result = land(repo, wt_tid, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id

        landed = load_all(repo)
        assert landed.is_ok
        assert final_id in landed.danger_ok
        assert main_tid in landed.danger_ok
        assert landed.danger_ok[final_id].state == TicketState.DONE


class TestDraftFinalizeRewritesCodeAndLeavesWorktreeClean:
    """Reviewer bug 1: `finalize_draft` rewrites tickets.md AND every code
    file carrying a `frob:ticket <draft-id>` directive, uncommitted, in the
    worktree -- but the old `land` squashed from the branch's last commit,
    which predated those rewrites. A landed source file kept the dangling
    draft id, and the worktree was left dirty after a "successful" land.
    `land` must commit finalize/close's changes in the worktree BEFORE the
    squash so both the ledger AND the rewritten code reach main, and the
    worktree ends up clean."""

    def test_code_directive_rewritten_and_worktree_clean_after_land(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-i", str(wt)], repo)

        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing2.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        # A code file carrying a frob:ticket directive naming the DRAFT id --
        # renumber_one (finalize_draft's rename primitive) must rewrite this
        # reference, and that rewrite must actually reach main.
        (wt / "src" / "thing2.py").write_text(
            f"# frob:ticket {draft_id}\ndef f():\n    pass\n"
        )
        _commit_all(wt, "off-branch ticket with a code directive")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id
        assert final_id != draft_id

        # The landed file on MAIN must carry the FINAL id, never the draft.
        landed_src = (repo / "src" / "thing2.py").read_text()
        assert draft_id not in landed_src
        assert f"frob:ticket {final_id}" in landed_src

        # The worktree must be left completely clean -- finalize/close's
        # writes were committed before the squash, not left dangling.
        wt_status = _run(["git", "status", "--porcelain"], wt).stdout.strip()
        assert wt_status == "", f"worktree left dirty: {wt_status!r}"

        # And the worktree's own copy of the file must ALSO carry the final
        # id (the commit-before-squash fix touches the worktree itself).
        wt_src = (wt / "src" / "thing2.py").read_text()
        assert draft_id not in wt_src
        assert f"frob:ticket {final_id}" in wt_src


class TestDraftFinalizeRewritesRegistryYamlRefs:
    """T-0577: draft finalize at land time (`renumber_one`) used to rewrite
    only `frob:` directive lines -- a registry yaml's `disposition:
    "deferred:<draft-id>"` value (docs/design/registry/*.yaml's grammar,
    `frob.registry._models.parse_disposition`) was left pointing at the
    now-dead draft id, breaking REG003 until a human hand-swapped it (the
    real T-0388/compliance.yaml incident). `_rewrite_registry_references`
    must rewrite these too."""

    def test_registry_yaml_deferred_ref_rewritten_to_final_id(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-yaml", str(wt)], repo)

        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing3.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)

        registry_dir = wt / "docs" / "design" / "registry"
        registry_dir.mkdir(parents=True)
        (registry_dir / "compliance.yaml").write_text(
            f'entries:\n  - id: some-check\n    disposition: "deferred:{draft_id}"\n'
        )
        (wt / "src" / "thing3.py").write_text("def f():\n    pass\n")
        _commit_all(wt, "off-branch ticket deferred in a registry yaml")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != draft_id

        landed_yaml = (
            repo / "docs" / "design" / "registry" / "compliance.yaml"
        ).read_text()
        assert draft_id not in landed_yaml
        assert f'"deferred:{final_id}"' in landed_yaml


class TestArchiveResurrection:
    """Reviewer bug 2: `splice_ledger` only read active tickets.md, never
    tickets-archive.md -- an id archived on main after the branch point
    would survive the ours-union and land back into main's active ledger,
    resurrecting a duplicate-id class a human previously had to resolve by
    hand at merge time (T-0176's own 0bb02cf merge). `land` must never
    reintroduce an already-archived id."""

    def test_archived_id_never_resurrected(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::splice_ledger kind="unit"
        # Seed a ticket that exists (stale, still active) in the worktree's
        # ledger view, then archive it on MAIN after the branch point --
        # simulating a branch whose base predates the archive.
        stale = new_ticket(repo, _spec("Will be archived"))
        assert stale.is_ok
        stale_id = stale.danger_ok.id
        _commit_all(repo, "file the soon-to-be-archived ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-j", str(wt)], repo)

        # Main independently closes and archives it AFTER the worktree
        # branched -- the worktree's tickets.md still has it as active.
        assert transition(repo, stale_id, TicketState.PLANNED).is_ok
        assert transition(repo, stale_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(repo)
        stale_ticket = loaded.danger_ok[stale_id]
        stale_ticket = stale_ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": stale_ticket.body + "\n## Done report\n\ndone\n",
            }
        )
        assert write_ticket(repo, stale_ticket).is_ok
        assert transition(repo, stale_id, TicketState.DONE).is_ok
        from frob.tickets import archive

        archived_count = archive(repo)
        assert archived_count.is_ok and archived_count.danger_ok == 1
        _commit_all(repo, "archive the stale ticket")

        # Now land unrelated worktree work; the worktree's own tickets.md
        # STILL carries stale_id as active (it branched before the archive).
        created = new_ticket(wt, _spec("Unrelated land", scope=("src/unrelated2.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "unrelated2.py").write_text("# unrelated\n")
        _commit_all(wt, "unrelated worktree work")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        active = load_all(repo)
        assert active.is_ok
        assert stale_id not in active.danger_ok, (
            f"{stale_id} resurrected into the active ledger by land"
        )

        archived = load_archive(repo)
        assert archived.is_ok
        assert stale_id in archived.danger_ok
        # Exactly once -- not duplicated across active+archive.
        assert list(load_all(repo).danger_ok).count(stale_id) == 0


class TestWipCommit:
    """`_wip_commit` -- uncommitted worktree changes at land time must be
    snapshotted before the merge that follows, both in dry-run (staged then
    unwound) and real (actually committed) mode."""

    def test_dry_run_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-dry", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip dry", scope=("src/wip_dry.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip dry ticket bits")

        # An UNCOMMITTED change present when land() is called.
        (wt / "src" / "wip_dry.py").write_text("# uncommitted at land time\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        # Dry run unwinds everything -- the uncommitted change is still
        # sitting uncommitted in the worktree afterward.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() != ""

    def test_real_land_wip_commits_uncommitted_changes(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-real", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip real", scope=("src/wip_real.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "wip_real.py").write_text("# committed baseline\n")
        _commit_all(wt, "wip real ticket bits")

        # An UNCOMMITTED change present when land() is called, real run.
        (wt / "src" / "wip_real.py").write_text("# uncommitted change to snapshot\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is True

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" in wt_log

        landed_content = (repo / "src" / "wip_real.py").read_text()
        assert landed_content == "# uncommitted change to snapshot\n"


class TestKindEvidenceMismatch:
    """`_validate_closeable`'s T-0215 kind-consistency guard: a non-docs-kind
    ticket carrying a `cmd:`-shaped evidence entry must never land, mirroring
    the write-time gate in `add_cmd_evidence`."""

    def test_non_docs_kind_with_cmd_evidence_refused(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-kind", str(wt)], repo)
        created = new_ticket(wt, _spec("Feature kind with cmd evidence"))
        assert created.is_ok
        tid = created.danger_ok.id

        loaded = load_all(wt)
        assert loaded.is_ok
        ticket = loaded.danger_ok[tid]
        # FEATURE is not in CMD_EVIDENCE_ALLOWED_KINDS ({DOCS}), but the
        # evidence entry has the exact cmd: shape (as if hand-pasted or the
        # kind was changed after the entry was recorded).
        ticket = ticket.model_copy(
            update={
                "evidence": ("cmd:pytest -q exit=0 sha256=abcdef012345",),
                "body": ticket.body + "\n## Done report\n\ndone\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "feature ticket with cmd evidence")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotCloseable


class TestUnownedDeletionRealRun:
    """The `_unowned_deletions` abort must behave identically in a real
    (non-dry-run) landing -- main untouched, worktree merge state aborted."""

    def test_unowned_deletion_aborts_on_real_run(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-real-del", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(
            wt, _spec("Unrelated real ticket", scope=("src/other2.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py, real run")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions

        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert (repo / "src" / "feature.py").exists()
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


class TestMergeConflictOutsideLedger:
    """`_merge_main_into_worktree` must abort loudly (not silently splice)
    on a real textual conflict in a NON-tickets.md file -- only tickets.md
    is resolved via `splice_ledger`; anything else conflicting must surface
    to a human."""

    def test_real_conflict_outside_tickets_md_aborts(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-conflict", str(wt)], repo)

        # Worktree modifies the SAME line of src/feature.py.
        (wt / "src" / "feature.py").write_text("# worktree-side edit\n")
        created = new_ticket(wt, _spec("Conflicting edit", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits feature.py")

        # Main independently modifies the SAME line, AFTER the worktree
        # branched -- a genuine textual conflict on a non-ticket file.
        (repo / "src" / "feature.py").write_text("# main-side edit\n")
        _commit_all(repo, "main edits feature.py")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.MergeConflict

        # _abort_merge must have run -- worktree left exactly as found.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""


class TestOutOfScopeConflictAutoResolved:
    """T-0479(b): a conflict in a file OUTSIDE the landing ticket's scope
    must auto-resolve to main's side instead of aborting the land."""

    def test_conflict_outside_scope_takes_mains_side_and_lands(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-oos", str(wt)], repo)

        # Worktree ticket is scoped ONLY to src/other.py; it never legitimately
        # touches feature.py.
        (wt / "src" / "other.py").write_text("worktree change\n")
        (wt / "src" / "feature.py").write_text("# worktree-side unrelated edit\n")
        created = new_ticket(
            wt, _spec("Out of scope conflict", scope=("src/other.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "worktree edits other.py and (out of scope) feature.py")

        # Main independently changes the SAME line of feature.py.
        (repo / "src" / "feature.py").write_text("# main-side edit\n")
        _commit_all(repo, "main edits feature.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        # Main's side of the out-of-scope conflict won.
        assert (repo / "src" / "feature.py").read_text() == "# main-side edit\n"
        assert (repo / "src" / "other.py").read_text() == "worktree change\n"


class TestDraftIdFinalization:
    """Incident class 3: a ticket filed off the default branch got a
    provisional T-draft-<hex> id; landing must finalize it to a real
    sequential id (T-0162's promised mechanism) before closing."""

    def test_draft_id_finalized_on_land(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-h", str(wt)], repo)

        # A worktree is, by definition, off the default branch -- new_ticket
        # mints a draft id here unconditionally.
        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/thing.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        (wt / "src" / "thing.py").write_text("# thing\n")
        _commit_all(wt, "off-branch ticket")

        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.final_id != draft_id
        assert not report.final_id.startswith("T-draft-")

        landed = load_all(repo)
        assert landed.is_ok
        assert draft_id not in landed.danger_ok
        assert report.final_id in landed.danger_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


# frob:ticket T-0637
class TestStandaloneSiblingDraftSurvivesLand:
    """T-0637 field incident: a worktree's ledger held a REAL ticket being
    landed AND a completely separate, standalone draft ticket (filed via
    `frob ticket new` mid-session, `frob:new`'s own scope-cut discovery --
    the T-0575/T-draft-3d5f6965 and T-0576's two-draft shapes). Before this
    fix, the sibling draft block was silently dropped by the land splice
    (never carried forward, since it was neither the ticket being landed
    nor already present on main) -- it must survive and land with a real,
    finalized id."""

    def test_sibling_draft_ticket_finalized_and_lands_alongside(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-j", str(wt)], repo)

        # The ticket actually being landed.
        primary = new_ticket(wt, _spec("Primary landed work", scope=("src/main3.py",)))
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        _make_closeable(wt, primary_id)
        (wt / "src" / "main3.py").write_text("# primary work\n")

        # A STANDALONE sibling, filed while working the primary ticket,
        # left QUEUED -- never touched again, never landed on its own.
        sibling = new_ticket(
            wt, _spec("Found while working the primary ticket", scope=("src/sib.py",))
        )
        assert sibling.is_ok
        sibling_draft_id = sibling.danger_ok.id
        assert sibling_draft_id.startswith("T-draft-")
        assert sibling_draft_id != primary_id

        _commit_all(wt, "primary work plus a standalone sibling draft ticket")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok

        # The sibling draft must NOT have vanished, and must NOT still
        # carry a draft id on main (T-0162: drafts never persist there).
        assert sibling_draft_id not in landed_map, (
            "sibling draft id should have been finalized away, not landed verbatim"
        )
        finalized_siblings = [
            tid
            for tid, t in landed_map.items()
            if t.title == "Found while working the primary ticket"
        ]
        assert finalized_siblings, "standalone sibling draft ticket was dropped at land"
        assert len(finalized_siblings) == 1
        sibling_final_id = finalized_siblings[0]
        assert not sibling_final_id.startswith("T-draft-")
        assert sibling_final_id != report.final_id

        # It survives in whatever state it was left in (QUEUED) -- landing
        # the PRIMARY ticket must not itself close/alter the sibling.
        assert landed_map[sibling_final_id].state == TicketState.QUEUED
        assert landed_map[report.final_id].state == TicketState.DONE


class TestLandNotFound:
    """`land` on a ticket id the worktree's store has never heard of."""

    def test_unknown_ticket_id_returns_not_found(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nf", str(wt)], repo)

        result = land(repo, "T-9999", wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.NotFound


class TestGitSubprocessFailures:
    """`land`'s own git-failure early returns -- each wraps a `run_argv`
    call whose failure is otherwise only reachable via a real, hard-to-
    reproduce environment fault (permission denial, disk full, a corrupted
    ref). Deterministically forced here via `_failing_run_argv` patching
    the module's single `run_argv` import point."""

    def test_main_dirty_check_git_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l1", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(repo) in argv and "status" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_main_branch_lookup_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l2", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # `current_branch` (frob.gitio) has its own internal `run_argv`
        # reference, independent of the one `_land.py` imports -- patch the
        # symbol `_land.py` calls directly rather than the git subprocess
        # layer, to exercise `land`'s own `main_branch.is_err` branch.
        def _fail(root: Path) -> Any:
            return Err(GitError.GitFailed)

        monkeypatch.setattr(_land_mod, "current_branch", _fail)
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_wip_commit_status_check_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l3", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "status" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_merge_command_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l4", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")
        (repo / "src" / "extra.py").write_text("# extra main commit\n")
        _commit_all(repo, "main moves on")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(wt) in argv and "merge" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_unowned_deletions_diff_failure_after_merge(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l5", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l5.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l5.py").write_text("# l5\n")
        _commit_all(wt, "wip")
        (repo / "src" / "extra2.py").write_text("# extra main commit\n")
        _commit_all(repo, "main moves on")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(wt) in argv and "diff" in argv and "--diff-filter=D" in argv
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # The merge that already landed in the worktree must have been
        # aborted -- no half-applied merge state left behind.
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""

    def test_squash_command_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l6", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l6.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l6.py").write_text("# l6\n")
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: str(repo) in argv and "--squash" in argv,
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_final_commit_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l7", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l7.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l7.py").write_text("# l7\n")
        _commit_all(wt, "wip")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(repo) in argv and "commit" in argv and "--squash" not in argv
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.CommitFailed


class TestLandDeeperBranches:
    """Additional `land`-body branches unreachable via ordinary happy/error
    fixture paths: the post-merge commit and finalize/close git-failure
    branches, each forced deterministically via monkeypatch since a real
    reproduction (disk full, permission denial mid-land) is impractical to
    fixture."""

    def test_unowned_deletion_real_run_with_actual_merge(self, repo: Path) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l8", str(wt)], repo)

        (wt / "src" / "feature.py").unlink()
        created = new_ticket(wt, _spec("Unrelated", scope=("src/other8.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "accidentally delete feature.py")

        # Main gains a commit AFTER the worktree branched, so merging main
        # into the worktree is a REAL merge (did_merge=True), not a no-op --
        # exercising the `if did_merge: _abort_merge(...)` branch under the
        # unowned-deletion abort, in a real (non-dry-run) land.
        (repo / "src" / "unrelated8.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.UnownedDeletions
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() == ""
        assert (repo / "src" / "feature.py").exists()

    def test_post_merge_commit_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l9", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l9.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l9.py").write_text("# l9\n")
        _commit_all(wt, "wip")

        (repo / "src" / "unrelated9.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        _failing_run_argv(
            monkeypatch,
            lambda argv: (
                str(wt) in argv
                and "commit" in argv
                and any("merge" in a and "landing" in a for a in argv)
            ),
            hard_err=True,
        )
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_finalize_draft_failure(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        import frob.tickets as tickets_mod

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l10", str(wt)], repo)
        created = new_ticket(wt, _spec("Filed off-branch", scope=("src/l10.py",)))
        assert created.is_ok
        draft_id = created.danger_ok.id
        assert draft_id.startswith("T-draft-")
        _make_closeable(wt, draft_id)
        (wt / "src" / "l10.py").write_text("# l10\n")
        _commit_all(wt, "off-branch ticket")

        from frob.tickets._models import TicketError

        monkeypatch.setattr(
            tickets_mod, "finalize_draft", lambda *a, **k: Err(TicketError.NotFound)
        )
        result = land(repo, draft_id, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed

    def test_worktree_branch_lookup_failure_after_close(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-l11", str(wt)], repo)
        created = new_ticket(wt, _spec("Whatever", scope=("src/l11.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "l11.py").write_text("# l11\n")
        _commit_all(wt, "wip")

        real_current_branch = _land_mod.current_branch

        def _fake(root: Path) -> Any:
            if str(root) == str(wt):
                return Err(GitError.GitFailed)
            return real_current_branch(root)

        monkeypatch.setattr(_land_mod, "current_branch", _fake)
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed


class TestPreworkSweepRefresh:
    """T-0236: an unrelated main landing that touches a ticket's scope globs
    moves its recorded pre-work sweep's scope digest out from under it --
    three consecutive reviews (T-0181, T-0203, T-0202) REJECTed solely or
    partly on this stale-PRE001 churn. `land` must refresh the sweep
    post-merge, pre-close so a ticket left in-progress after a landing
    failure (or a reviewer's `frob check --ticket` run in the interim)
    never sees a sweep stale for a reason outside the ticket's own control."""

    def test_land_refreshes_stale_sweep_after_unrelated_main_change(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_refresh_prework_sweep kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sweep", str(wt)], repo)

        created = new_ticket(wt, _spec("Sweep refresh", scope=("src/feature.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Record a deliberately stale sweep -- this mirrors what `frob
        # ticket start` recorded before main moved.
        stale = PreworkSweep(
            date=date.today(), dup_findings=0, xref_hits=(), digest="stale-digest"
        )
        assert record_prework(wt, tid, stale).is_ok

        # main lands an UNRELATED commit that happens to touch the ticket's
        # scoped file -- the drift class this ticket is about.
        (repo / "src" / "feature.py").write_text("# landed feature, updated\n")
        _commit_all(repo, "unrelated main-side edit to a scope-owned file")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        # The sweep recorded in the worktree during land's post-merge,
        # pre-close refresh must reflect the POST-merge tree, not the stale
        # one recorded before `land` ran.
        refreshed = load_prework(wt, tid)
        assert refreshed is not None
        assert refreshed.digest != "stale-digest"

        graph = build_graph(wt, wt / ".frob" / "cache.db")
        assert graph.is_ok
        assert refreshed.digest == scope_digest(("src/feature.py",), graph.danger_ok)

    def test_sweep_refresh_failure_does_not_block_landing(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_refresh_prework_sweep kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-sweep-fail", str(wt)], repo)

        created = new_ticket(wt, _spec("Sweep refresh failure", scope=("src/x.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "x.py").write_text("# x\n")
        _commit_all(wt, "add x")

        import frob.gates as gates_mod
        from frob.gates._models import GateError

        monkeypatch.setattr(
            gates_mod, "sweep_ticket", lambda *a, **k: Err(GateError.WriteFailed)
        )

        # `land` must still succeed -- the sweep refresh is best-effort and
        # is not what gates landing (close's own evidence/Done-report checks
        # are).
        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err


class TestLandCompleteness:
    """T-0463: `land` must bring the worktree's COMPLETE changeset (tracked
    edits + untracked new files + deletions), not just what a `git diff
    HEAD` patch would see, and must assert this BEFORE committing -- the
    root cause of the T-0448 `docs/modules/render.md` loss was a surgical
    git-diff/patch land that silently dropped an untracked file with no
    error."""

    def test_land_brings_tracked_edit_untracked_new_file_and_deletion(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_assert_land_complete kind="unit"
        # frob:tests src/frob/tickets/_land.py::_worktree_full_changeset kind="unit"
        # `doomed.py` must exist BEFORE the worktree branches, so its
        # deletion has a real net effect relative to main (a file created
        # and deleted within the same branch history nets to "no change"
        # against main and would not exercise the deletion path at all).
        (repo / "src" / "doomed.py").write_text("# present before branch\n")
        _commit_all(repo, "add doomed.py (present before branch)")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-complete", str(wt)], repo)
        created = new_ticket(
            wt,
            _spec(
                "Complete changeset",
                scope=("src/feature.py", "src/brand_new.py", "src/doomed.py"),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # (a) a tracked EDIT to a file main already has. (b) an uncommitted
        # DELETION of a file main already has -- exercises the wip-commit's
        # `git add -A` staging a deletion.
        (wt / "src" / "feature.py").write_text("# tracked edit\n")
        (wt / "src" / "doomed.py").unlink()

        # (c) an UNTRACKED new file, left uncommitted at land time -- the
        # exact T-0448 incident class.
        (wt / "src" / "brand_new.py").write_text("# brand new, never committed\n")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        assert (repo / "src" / "feature.py").read_text() == "# tracked edit\n"
        assert (repo / "src" / "brand_new.py").exists()
        assert not (repo / "src" / "doomed.py").exists()

        # The completeness assertion actually ran and saw all three paths,
        # and every one of them landed in the final commit.
        assert "src/feature.py" in report.worktree_changeset
        assert "src/brand_new.py" in report.worktree_changeset
        assert "src/doomed.py" in report.worktree_changeset
        for path in report.worktree_changeset:
            assert path in report.files_changed

    def test_incomplete_land_fails_loudly_and_commits_nothing(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_assert_land_complete kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-incomplete", str(wt)], repo)
        created = new_ticket(wt, _spec("Incomplete", scope=("src/gadget2.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "gadget2.py").write_text("# gadget2\n")
        _commit_all(wt, "add gadget2")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # Simulate a dropped file: the worktree "changed" a path the
        # squash-apply never actually staged (the T-0448 incident, forced
        # deterministically instead of relying on a real patch-based land
        # to reproduce it).
        real_changeset = _land_mod._worktree_full_changeset

        def _fake_changeset(worktree: Path, main_branch_name: str) -> Any:
            result = real_changeset(worktree, main_branch_name)
            if result.is_err:
                return result
            return Ok(result.danger_ok | {"src/phantom_dropped.py"})

        monkeypatch.setattr(_land_mod, "_worktree_full_changeset", _fake_changeset)

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        assert "src/phantom_dropped.py" in caplog.text

        # The commit must never have happened, and the squash must have
        # been fully unwound -- root is exactly as found, not partially
        # staged or partially committed.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    def test_worktree_pointed_at_same_branch_as_main_is_refused_not_silently_empty(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_worktree_full_changeset kind="unit"
        # frob:tests src/frob/tickets/_land.py::_true_merge_base kind="unit"
        """T-0761 regression: the real T-0640 incident. `land()` was invoked
        with `--worktree` pointing at the SAME checkout/branch `root` had
        checked out -- no distinct feature branch was ever created. A NEW
        source file was added and committed directly on that shared branch
        (mirroring the incident's `src/frob/strata/_reliability.py`), then
        `land(repo, tid, repo)` ran.

        Before the T-0761 fix, this landed "successfully": the merge/squash
        steps against `worktree`'s own branch were git no-ops (a branch
        merged/squashed into itself), so the T-0463 completeness assertion's
        `expected` changeset came back EMPTY and passed vacuously -- only the
        version-bump/ledger-splice writes ended up in the final commit, and
        `new_feature.py` was silently dropped even though `frob ticket land`
        reported success. After the fix, `land` must refuse with
        `IncompleteLand` (a completeness error) rather than commit a
        changeset that drops the new file -- the ticket's acceptance
        criterion's second branch."""
        (repo / "src" / "new_feature.py").write_text("# brand new feature code\n")
        _commit_all(repo, "add new_feature.py directly on the shared branch")

        created = new_ticket(
            repo, _spec("Same-branch land", scope=("src/new_feature.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on the shared branch")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand

        # Refused, not silently landed: no "land T-XXXX" squash-apply commit
        # (the false-green signature -- version bump + ledger only) was ever
        # made, the squash-stage was unwound cleanly, and `new_feature.py`'s
        # content is exactly what was committed above -- nothing was dropped
        # by an incomplete commit.
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "land " not in log
        assert _status_ignoring_frob(repo) == ""
        assert (repo / "src" / "new_feature.py").read_text() == (
            "# brand new feature code\n"
        )


# frob:ticket T-0338
class TestReleaseBump:
    """T-0338: `land`'s optional `bump_version` callback -- the REL001
    version-bump/stamp coordinator step folded into `land` itself."""

    def test_bump_applied_and_reported(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_bump_applied_and_reported  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-bump", str(wt)], repo)
        created = new_ticket(wt, _spec("Bump me", scope=("src/bumped.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "bumped.py").write_text("# bumped\n")
        _commit_all(wt, "add bumped.py")

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "VERSION_BUMPED").write_text(final_id)
            _run(["git", "add", "VERSION_BUMPED"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.release_bumped_to == "1.2.3"
        assert (repo / "VERSION_BUMPED").exists()
        # The bump's own write must have landed in the SAME commit as the
        # squash-apply, not a separate uncommitted change.
        assert _status_ignoring_frob(repo) == ""

    def test_no_bump_needed_reports_none(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_no_bump_needed_reports_none  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nobump", str(wt)], repo)
        created = new_ticket(wt, _spec("No bump needed", scope=("src/quiet.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "quiet.py").write_text("# quiet\n")
        _commit_all(wt, "add quiet.py")

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Ok(None),
        )
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to is None

    def test_bump_failure_unwinds_squash(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_bump_failure_unwinds_squash  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-badbump", str(wt)], repo)
        created = new_ticket(wt, _spec("Bad bump", scope=("src/badbump.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "badbump.py").write_text("# bad bump\n")
        _commit_all(wt, "add badbump.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Err(LandError.ReleaseBumpFailed),
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""

    def test_no_callback_is_noop(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestReleaseBump.test_no_callback_is_noop  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-nocallback", str(wt)], repo)
        created = new_ticket(wt, _spec("No callback", scope=("src/nc.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "nc.py").write_text("# no callback\n")
        _commit_all(wt, "add nc.py")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to is None


# frob:ticket T-0338
class TestRebuildNatives:
    """T-0338: `land`'s optional `rebuild_natives` callback -- invoked only
    when the landed changeset touches a native source tree."""

    def test_invoked_when_native_source_touched(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_invoked_when_native_source_touched  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-src", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Native change", scope=("frob-core/src/lib.rs",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "frob-core").mkdir()
        (wt / "frob-core" / "src").mkdir()
        (wt / "frob-core" / "src" / "lib.rs").write_text("// native change\n")
        _commit_all(wt, "touch frob-core")

        calls: list[Path] = []

        def rebuild_natives(root: Path) -> bool:
            calls.append(root)
            return True

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=rebuild_natives)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is True
        assert calls == [repo]

    def test_skipped_when_no_native_source_touched(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_skipped_when_no_native_source_touched  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-not-native", str(wt)], repo)
        created = new_ticket(wt, _spec("Regular change", scope=("src/regular.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "regular.py").write_text("# regular\n")
        _commit_all(wt, "add regular.py")

        calls: list[Path] = []

        def rebuild_natives(root: Path) -> bool:
            calls.append(root)
            return True

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=rebuild_natives)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is False
        assert calls == []

    def test_rebuild_failure_does_not_block_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestRebuildNatives.test_rebuild_failure_does_not_block_land  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-native-fail", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Native change fails rebuild", scope=("strata-core/src/lib.rs",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "strata-core").mkdir()
        (wt / "strata-core" / "src").mkdir()
        (wt / "strata-core" / "src" / "lib.rs").write_text("// native change\n")
        _commit_all(wt, "touch strata-core")

        result = land(repo, tid, wt, dry_run=False, rebuild_natives=lambda root: False)
        assert result.is_ok, result.err
        assert result.danger_ok.natives_rebuilt is False


# frob:ticket T-0682
class TestMergeMainIntoWorktreeRicherState:
    """T-0682 integration lock: `_merge_main_into_worktree` (the "merge main
    into the worktree" stage every `frob ticket land` call runs, and the
    exact site where the registered `tickets.md` git merge driver
    auto-fires on `git merge --no-commit --no-ff`) must not let main's
    bare, reportless copy of the LANDING ticket's own block win over the
    worktree's Done-reported copy WHEN the worktree's copy also outranks
    it -- the original T-0682 field incident."""

    def test_landing_tickets_in_progress_report_survives_the_merge_stage(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestMergeMainIntoWorktreeRicherState.test_landing_tickets_in_progress_report_survives_the_merge_stage  # noqa: E501
        # Ticket is created ON main (a real id, not a draft) so it exists
        # in BOTH the worktree's and main's ledgers before either side
        # diverges it -- the scenario under test is a genuine same-id
        # divergence, not draft finalization (covered elsewhere).
        created = new_ticket(repo, _spec("Landing ticket", scope=("src/widget.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _commit_all(repo, "file landing ticket")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-richer", str(wt)], repo)

        # Worktree: driven to `in-progress` with a substantive Done report
        # already attached -- a HIGHER state-rank than main's bare queued
        # AND a Done report, matching the real field incident (T-0633/
        # T-0637's landing tickets were in-progress+reported when the
        # merge stage regressed them).
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt).danger_ok[tid]
        with_report = loaded.model_copy(
            update={
                "body": loaded.body
                + "\n## Done report\n\nSubstantive report text here.\n"
            }
        )
        assert write_ticket(wt, with_report).is_ok
        (wt / "src" / "widget.py").write_text("# new widget\n")
        _commit_all(wt, "advance ticket to in-progress+report")
        ticket_before_merge = load_all(wt).danger_ok[tid]

        # Main's OWN copy of the SAME ticket never advanced past its bare
        # `queued` state -- unrelated main-side history, no divergence in
        # rank OR report to work in the worktree's favor by accident.
        (repo / "src" / "unrelated.py").write_text("# unrelated main commit\n")
        _commit_all(repo, "unrelated main-side commit")

        result = _land_mod._merge_main_into_worktree(
            repo, wt, ticket_before_merge, "main"
        )
        assert result.is_ok, result.err

        merged_text = ledger_path(wt).read_text()
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(merged_text).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "## Done report" in parsed[tid].body


class TestUnboundAcceptancePreflightBeforeMerge:
    """T-0763: an unbound acceptance criterion must be caught by land's
    PRE-merge closeability preflight (`_validate_closeable` ->
    `_validate_acceptance_bound`), not discovered only after the merge/
    finalize commits are already made. Before this fix, `_validate_closeable`
    checked only evidence-present/Done-report/cmd-evidence-kind, so an
    unbound acceptance criterion sailed through the precheck, `land` merged
    main into the worktree AND committed a finalize commit, and only then
    failed at `_close_finalized_ticket`'s `transition(..., DONE)` call with
    `LandError.CloseFailed` -- leaving a merge/finalize commit the caller
    had to `git reset --hard HEAD~1` before retrying. This test asserts the
    ENTIRE git log (both `repo`/main and `wt`/worktree) is byte-identical
    before and after the refused land -- not just that `land` returns an
    error -- since a fail-AFTER-merge regression would still return
    `Err(...)` while leaving exactly the commit(s) this asserts are absent.
    """

    def test_unbound_acceptance_refused_pre_merge_no_commits_created(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUnboundAcceptancePreflightBeforeMerge.test_unbound_acceptance_refused_pre_merge_no_commits_created  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-unbound-acceptance", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with unbound acceptance", scope=("src/other3.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id

        # Attach an acceptance criterion whose own `evidence` tuple is
        # empty -- unbound by construction (T-0572) -- while the ticket
        # otherwise satisfies every OTHER closeability precondition
        # (evidence present, Done report present, evidence-kind
        # consistent), isolating this test to the acceptance-binding gate
        # alone.
        _make_closeable(wt, tid)
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "acceptance": (
                    AcceptanceCriterion(text="GIVEN x WHEN y THEN z", evidence=()),
                )
            }
        )
        assert write_ticket(wt, ticket).is_ok
        _commit_all(wt, "advance ticket with unbound acceptance criterion")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout
        wt_status_before = _status_ignoring_frob(wt)

        result = land(repo, tid, wt, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Git log is UNCHANGED on both sides -- no merge commit, no
        # finalize commit, no squash-apply commit -- not merely "the same
        # HEAD sha", but the exact same full set of commits (a fail-after-
        # merge regression would add commits reachable only via a branch
        # ref, which `--all` catches even if `HEAD` itself were untouched).
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before
        # Working tree is clean -- no merge left half-applied/uncommitted.
        assert _status_ignoring_frob(wt) == wt_status_before
        assert _status_ignoring_frob(repo) == ""

        # The ticket itself is untouched: still in-progress, not closed.
        still = load_all(wt).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS


class TestScopeUnboundPreflightBeforeMerge:
    """T-0774: `EvidenceScopeUnbound` (D-05's injected `covers_scope`
    callable) must ALSO be caught by land's PRE-merge closeability
    preflight (`_land_precheck` -> `_validate_scope_covered_preflight`),
    not discovered only after the merge/finalize commits already exist.
    Before this fix, `_land_precheck` never consulted `covers_scope` at
    all -- it was invoked for the first time inside `_land_finalize_and_close`,
    AFTER the merge commit was already made, so a ticket whose evidence does
    not cover its scope still merged+committed before `land` refused
    (`LandError.CloseFailed`, not `NotCloseable`). This test asserts the
    ENTIRE git log (both `repo`/main and `wt`/worktree) is byte-identical
    before and after the refused land -- not just that `land` returns an
    error -- mirroring `TestUnboundAcceptancePreflightBeforeMerge`'s own
    assertion shape for the sibling D-05 check this ticket closes."""

    def test_scope_unbound_refused_pre_merge_no_commits_created(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge.test_scope_unbound_refused_pre_merge_no_commits_created  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-scope-unbound", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with scope-unbound evidence", scope=("src/other4.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id

        # Otherwise fully closeable (evidence present, Done report present,
        # no unbound acceptance criteria) -- isolating this test to the
        # covers_scope preflight alone.
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with scope-unbound evidence")

        main_log_before = _run(["git", "log", "--oneline", "--all"], repo).stdout
        wt_log_before = _run(["git", "log", "--oneline", "--all"], wt).stdout
        wt_status_before = _status_ignoring_frob(wt)

        # A `covers_scope` callable that always answers False, exactly the
        # shape `frob.app.ticket_runner`'s `_land_covers_scope_fn` supplies
        # via `frob.gates.evidence_covers_scope` when no evidence id binds
        # to a touched/scope symbol.
        result = land(repo, tid, wt, dry_run=False, covers_scope=lambda _t: False)

        assert result.is_err
        assert result.danger_err == LandError.NotCloseable

        # Git log is UNCHANGED on both sides -- no merge commit, no
        # finalize commit, no squash-apply commit.
        assert (
            _run(["git", "log", "--oneline", "--all"], repo).stdout == main_log_before
        )
        assert _run(["git", "log", "--oneline", "--all"], wt).stdout == wt_log_before
        # Working tree is clean -- no merge left half-applied/uncommitted.
        assert _status_ignoring_frob(wt) == wt_status_before
        assert _status_ignoring_frob(repo) == ""

        # The ticket itself is untouched: still in-progress, not closed.
        still = load_all(wt).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS

    def test_covers_scope_true_still_lands_normally(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestScopeUnboundPreflightBeforeMerge.test_covers_scope_true_still_lands_normally  # noqa: E501
        wt = repo.parent / "wt"
        _run(
            ["git", "worktree", "add", "-b", "feature-scope-bound", str(wt)],
            repo,
        )

        created = new_ticket(
            wt,
            _spec("Ticket with scope-bound evidence", scope=("src/other5.py",)),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "advance ticket with scope-bound evidence")

        result = land(repo, tid, wt, dry_run=False, covers_scope=lambda _t: True)

        assert result.is_ok, result.err


# frob:ticket T-0795
class TestLandRetryAfterFinalizeThenFail:
    """T-0795: three real lands this drive (T-0676, T-0774, T-0767) merged
    and finalized in the worktree (the ticket transitioned to `done` and
    that transition was committed there) but then failed at a LATER step
    -- the squash-apply onto `root` -- before the main commit landed.
    Retrying the identical `land()` call always errored `InvalidTransition`
    (`transition(..., DONE)` re-run against an already-`done` ticket), even
    though the land itself is perfectly resumable; each incident required a
    manual splice-apply onto main instead. This locks the fix: a retry
    recognizes the already-done ticket and resumes straight at
    squash-apply."""

    def test_retry_after_finalize_then_squash_failure_lands_the_diff(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_after_finalize_then_squash_failure_lands_the_diff  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_close_finalized_ticket kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-retry", str(wt)], repo)
        created = new_ticket(wt, _spec("Retry me", scope=("src/retried.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "retried.py").write_text("# retried feature\n")
        _commit_all(wt, "add retried.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        # First attempt: `bump_version` fails (simulating whichever
        # post-finalize step actually failed in the real incidents --
        # squash conflict, REL001 bump, or the T-0463 completeness
        # assertion; all of them unwind `root` cleanly via `reset --hard`
        # the same way this callback's failure path does) AFTER the
        # worktree has already merged, finalized, and closed the ticket
        # (that whole sequence commits in the WORKTREE unconditionally
        # before `_land_squash_apply` -- see `_land_locked` -- so it
        # survives this failure).
        first = land(
            repo,
            tid,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Err(LandError.ReleaseBumpFailed),
        )
        assert first.is_err
        assert first.danger_err == LandError.ReleaseBumpFailed

        # root: untouched by the failed attempt (the bump failure unwound
        # the staged squash).
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _status_ignoring_frob(repo) == ""

        # worktree: the ticket really did reach `done` and that transition
        # really did commit -- this is the exact precondition that used to
        # make the retry below error `InvalidTransition`. The first attempt
        # already finalized `tid`'s draft id to a real sequential id (that
        # finalize-and-commit step runs BEFORE the bump that then failed),
        # so the retry -- exactly like a real coordinator's retry -- must
        # address the ticket by its now-finalized id.
        wt_tickets = load_all(wt).danger_ok
        final_id = next(i for i, t in wt_tickets.items() if t.state == TicketState.DONE)
        assert final_id != tid
        assert _status_ignoring_frob(wt) == ""

        # Retry, identical arguments (final id, same worktree) except a
        # bump_version that now succeeds -- must NOT error InvalidTransition
        # on the already-done ticket; must resume at squash-apply and
        # actually land.
        second = land(
            repo,
            final_id,
            wt,
            dry_run=False,
            bump_version=lambda root, ticket, fid: Ok(None),
        )
        assert second.is_ok, second.err
        assert second.danger_ok.final_id == final_id

        # The diff really landed onto main: the new file exists on root's
        # branch, in a real "land <id>" commit distinct from before_main_sha.
        assert (repo / "src" / "retried.py").read_text() == "# retried feature\n"
        after_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_main_sha != before_main_sha
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert f"land {final_id}" in log
        assert _status_ignoring_frob(repo) == ""

    def test_retry_when_still_queued_re_runs_the_ordinary_transition(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRetryAfterFinalizeThenFail.test_retry_when_still_queued_re_runs_the_ordinary_transition  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_close_finalized_ticket kind="unit"
        """Sanity companion: the ordinary (non-retry) first-time land, where
        the ticket is NOT already done, still runs the real transition --
        the T-0795 fix only short-circuits when the ticket is ALREADY
        `done`, it does not skip closing altogether."""
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-firsttime", str(wt)], repo)
        created = new_ticket(wt, _spec("First time", scope=("src/firsttime.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "firsttime.py").write_text("# first time\n")
        _commit_all(wt, "add firsttime.py")

        assert load_all(wt).danger_ok[tid].state == TicketState.IN_PROGRESS

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        assert result.danger_ok.final_id != ""


# frob:ticket T-0795
class TestLandRefusesWhenRootIsWorktree:
    """T-0795: `land()` invoked with `--worktree` resolving to the SAME
    path as `root` used to fall through to `_worktree_full_changeset`'s
    much later T-0640/T-0761 diagnosis ("`--worktree` almost certainly
    points at the same checkout/branch root has checked out ... create a
    real feature branch") -- a correct remedy for a worktree genuinely
    pointed at the wrong branch, but a misleading one for the far more
    common real cause: `root` defaults to the invoker's cwd, so running
    `frob ticket land` from a shell sitting INSIDE the worktree makes
    `root` resolve to `worktree` for free. This locks the new EARLY
    refusal (before any git mutation) that names the real mistake."""

    def test_refused_before_any_git_mutation_names_the_real_mistake(
        self, repo: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree.test_refused_before_any_git_mutation_names_the_real_mistake  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        created = new_ticket(
            repo, _spec("Same path as root", scope=("src/samepath.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on root")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        with caplog.at_level("ERROR", logger="frob.tickets._land"):
            result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        assert "cwd" in caplog.text
        assert "ROOT checkout" in caplog.text

        # Refused before any git mutation at all: no merge/finalize/squash
        # commit, HEAD unmoved, tree exactly as found.
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _status_ignoring_frob(repo) == ""
        still = load_all(repo).danger_ok[tid]
        assert still.state == TicketState.IN_PROGRESS

    def test_still_refuses_when_worktree_has_diverged_commits(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRefusesWhenRootIsWorktree.test_still_refuses_when_worktree_has_diverged_commits  # noqa: E501
        # frob:tests src/frob/tickets/_land.py::_refuse_if_root_is_worktree kind="unit"
        """T-0761 regression preserved under a different name: the exact
        prior scenario (a new file committed directly on the branch `root`
        has checked out, then `land(repo, tid, repo)`) still refuses with
        `IncompleteLand` -- just via the new, earlier, more specific check
        rather than falling through to `_worktree_full_changeset`."""
        (repo / "src" / "new_feature2.py").write_text("# brand new feature code\n")
        _commit_all(repo, "add new_feature2.py directly on the shared branch")

        created = new_ticket(
            repo, _spec("Same-branch land 2", scope=("src/new_feature2.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(repo, tid)
        _commit_all(repo, "close ticket state directly on the shared branch")

        result = land(repo, tid, repo, dry_run=False)

        assert result.is_err
        assert result.danger_err == LandError.IncompleteLand
        log = _run(["git", "log", "--oneline"], repo).stdout
        assert "land " not in log
        assert _status_ignoring_frob(repo) == ""
