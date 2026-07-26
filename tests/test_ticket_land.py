"""T-0176: `frob ticket land` -- one-command landing.

Fixture-repo tests reproducing the real incident classes the ticket body
names: a stale-base worktree silently deleting a feature main already
landed, a `tickets.md` both-sides-append textual conflict, and provisional
(draft) id finalization at land time. Uses real git subprocesses (matching
tests/test_tickets_collision.py's style) -- not mocks -- because the whole
point of `land` is real merge/conflict/deletion behavior.
"""

from __future__ import annotations

import multiprocessing
import os
import signal
import subprocess
import time
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
    set_done_report,
    transition,
)
from frob.tickets._land import land, splice_ledger
from frob.tickets._models import (
    AcceptanceCriterion,
    DoneReportClaims,
    LandError,
    render_claims_block,
)
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


# frob:ticket T-0764
class TestSpliceLedgerPrefersEvidenceRichSideOnRankTie:
    """T-0764: the T-0753 field incident -- an in-flight worktree ticket
    with `start` + recorded evidence + a bound acceptance criterion but NO
    Done report yet, tied in state-rank (`in-progress`) with main's bare,
    reportless `in-progress` copy of the same id (e.g. after an
    archive/concurrent-ledger-rewrite reset the worktree's own view).
    Before T-0764 this fell straight to the old arbitrary `b`-wins
    tiebreak; now the evidence/acceptance-richer side must win."""

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie.test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie  # noqa: E501
    def test_evidence_and_acceptance_rich_side_wins_a_same_rank_reportless_tie(
        self, tmp_path: Path
    ) -> None:
        created = new_ticket(
            tmp_path,
            TicketSpec(
                title="Landing ticket",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                acceptance=(AcceptanceCriterion(text="GIVEN..WHEN..THEN.."),),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(tmp_path).danger_ok[tid]

        rich = loaded.model_copy(
            update={
                "evidence": ("tests/test_widget.py::test_x",),
                "acceptance": (
                    AcceptanceCriterion(
                        text="GIVEN..WHEN..THEN..",
                        evidence=("tests/test_widget.py::test_x",),
                    ),
                ),
            }
        )
        assert write_ticket(tmp_path, rich).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # `theirs`: same id, same rank, no Done report on EITHER side, but
        # bare -- no evidence, no bound acceptance -- exactly the
        # archive/concurrent-rewrite reset shape from the T-0753 incident.
        bare = loaded.model_copy(update={"evidence": (), "acceptance": ()})
        assert write_ticket(tmp_path, bare).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].evidence == ("tests/test_widget.py::test_x",)
        assert parsed[tid].acceptance[0].evidence == ("tests/test_widget.py::test_x",)

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerPrefersEvidenceRichSideOnRankTie.test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins  # noqa: E501
    def test_acceptance_binding_unioned_even_when_the_reportless_higher_rank_side_wins(
        self, tmp_path: Path
    ) -> None:
        """The `_union_acceptance` twin of D-09's `_union_evidence`: even
        when the WINNING side is picked for some other reason (here, a
        strictly higher rank), a criterion binding the LOSING side already
        had must not be silently dropped."""
        created = new_ticket(
            tmp_path,
            TicketSpec(
                title="Landing ticket",
                kind=TicketKind.BUG,
                origin=Origin.AGENT,
                acceptance=(AcceptanceCriterion(text="GIVEN..WHEN..THEN.."),),
            ),
        )
        assert created.is_ok
        tid = created.danger_ok.id
        loaded = load_all(tmp_path).danger_ok[tid]

        # `ours`: bare queued (rank 0) but with the criterion already bound.
        bound_but_low_rank = loaded.model_copy(
            update={
                "evidence": ("tests/test_widget.py::test_x",),
                "acceptance": (
                    AcceptanceCriterion(
                        text="GIVEN..WHEN..THEN..",
                        evidence=("tests/test_widget.py::test_x",),
                    ),
                ),
            }
        )
        assert write_ticket(tmp_path, bound_but_low_rank).is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # `theirs`: strictly higher rank (in-progress), unbound criterion,
        # no Done report -- this side wins on rank, but must inherit the
        # OTHER side's binding rather than dropping it.
        assert transition(tmp_path, tid, TicketState.PLANNED).is_ok
        assert transition(tmp_path, tid, TicketState.IN_PROGRESS).is_ok
        theirs_text = ledger_path(tmp_path).read_text()

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert parsed[tid].state == TicketState.IN_PROGRESS
        assert "tests/test_widget.py::test_x" in parsed[tid].evidence
        assert parsed[tid].acceptance[0].evidence == ("tests/test_widget.py::test_x",)


# frob:ticket T-0764
class TestSpliceLedgerIdDropGuard:
    """The structural guard the T-0367 incident demands: `splice_ledger`
    refuses loudly rather than silently committing a merge that drops an
    id (markerless-block class) or produces unparseable output."""

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_a_side_only_id_missing_from_theirs_survives_the_splice  # noqa: E501
    def test_a_side_only_id_missing_from_theirs_survives_the_splice(
        self, tmp_path: Path
    ) -> None:
        """Sanity: an id present on only ONE side (never archived) is not
        itself an integrity violation -- the normal union-by-id case."""
        created = new_ticket(tmp_path, _spec("Ours-only ticket"))
        assert created.is_ok
        tid = created.danger_ok.id
        ours_text = ledger_path(tmp_path).read_text()
        theirs_text = "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_ok
        from frob.tickets._store import _parse_ledger

        parsed = _parse_ledger(spliced.danger_ok).danger_ok
        assert tid in parsed

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_malformed_side_is_refused_not_silently_treated_as_empty  # noqa: E501
    def test_malformed_side_is_refused_not_silently_treated_as_empty(
        self, tmp_path: Path
    ) -> None:
        """A hand-corrupted input ledger (a marker present but its yaml
        frontmatter fence broken) fails `_parse_ledger` up front --
        `splice_ledger` must propagate that `Err`, never silently treat the
        unparseable side as if it carried zero tickets (which would make
        every id on the OTHER, well-formed side look like a one-sided
        addition instead of a real divergence needing a human's eyes)."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        ours_text = ledger_path(tmp_path).read_text()

        # Marker present, but no ```yaml fence follows it at all.
        theirs_text = "# Tickets\n\n<!-- ticket:T-9999 -->\nno yaml fence here\n"

        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_err

    # frob:ticket T-0764
    # frob:tests tests/test_ticket_land.py::TestSpliceLedgerIdDropGuard.test_render_that_would_drop_an_id_is_refused  # noqa: E501
    def test_render_that_would_drop_an_id_is_refused(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Direct unit-level pin on the guard itself: if the render step
        (patched here to simulate a future rendering regression) drops an
        id `_merge_ledger_tickets` produced, `splice_ledger` must refuse
        rather than commit the truncated text."""
        created = new_ticket(tmp_path, _spec("A ticket"))
        assert created.is_ok
        ours_text = ledger_path(tmp_path).read_text()
        theirs_text = "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        def _dropping_render(tickets: dict) -> str:
            # Simulate a render bug: silently omit every ticket's section.
            return "# Tickets\n\nCentral ledger managed by `frob ticket`.\n"

        monkeypatch.setattr(_land_mod, "_render_ledger", _dropping_render)
        spliced = splice_ledger(ours_text, theirs_text)
        assert spliced.is_err
        assert spliced.danger_err.name == "LedgerIntegrityViolation"


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


class TestPlannedStateAutoAdvanceOnLand:
    """T-0821: a ticket left in PLANNED (never run through `frob ticket
    start`, or reverted there by a section-10b ledger restore) but
    otherwise closeable (evidence + Done report) must land straight to
    DONE, not die `InvalidTransition` after main already merged."""

    # frob:ticket T-0821
    # frob:tests tests/test_ticket_land.py::TestPlannedStateAutoAdvanceOnLand.test_planned_ticket_with_full_evidence_lands_to_done  # noqa: E501
    def test_planned_ticket_with_full_evidence_lands_to_done(self, repo: Path) -> None:
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-planned", str(wt)], repo)
        created = new_ticket(wt, _spec("Add sprocket", scope=("src/sprocket.py",)))
        assert created.is_ok
        tid = created.danger_ok.id

        # Left in PLANNED (`frob ticket start`'s first transition), never
        # advanced to IN_PROGRESS -- but evidence and a Done report are
        # both present, exactly the T-0799/T-0752/T-0815 incident shape.
        assert transition(wt, tid, TicketState.PLANNED).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[tid]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok
        assert load_all(wt).danger_ok[tid].state == TicketState.PLANNED

        (wt / "src" / "sprocket.py").write_text("# new sprocket\n")
        _commit_all(wt, "add sprocket")

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok

        landed = load_all(repo)
        assert landed.is_ok
        assert landed.danger_ok[report.final_id].state == TicketState.DONE


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

        # T-0854: the ticket's own scope must cover the registry row it
        # defers to itself -- otherwise T-0854's live-tracker-citation
        # preflight (correctly) refuses to land a ticket while a registry
        # disposition still names it as the reason a compliance gap is
        # open, unless the ticket's own change is what resolves that row.
        created = new_ticket(
            wt,
            _spec(
                "Filed off-branch",
                scope=("src/thing3.py", "docs/design/registry/compliance.yaml"),
            ),
        )
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


class TestWipCommitNormalizationOnlyDirty:
    """T-0847: a worktree that is `_porcelain_dirty` purely because of a
    line-ending normalization status line (WSL/autocrlf phantom-modified)
    must not fail land with `GitFailed` -- `add -A` renormalizes back to the
    identical committed blob, so `git commit` has nothing real to commit and
    used to exit 1 with no stderr, wrongly surfaced as a land failure."""

    def test_normalization_only_dirty_worktree_treated_as_no_op_not_git_failed(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_do_wip_commit kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-wip-crlf", str(wt)], repo)
        created = new_ticket(wt, _spec("Wip crlf", scope=("src/wip_crlf.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)

        # Force text normalization on this worktree and commit an LF file
        # under it -- the committed blob is normalized LF content.
        _run(["git", "config", "core.autocrlf", "true"], wt)
        (wt / "src" / "wip_crlf.py").write_text("line one\nline two\n")
        _commit_all(wt, "wip crlf ticket bits")

        # Simulate the WSL phantom-dirty symptom: the working-tree file now
        # carries CRLF endings, so `git status --porcelain` reports it
        # modified, but `add -A` will renormalize it right back to the
        # identical committed blob (nothing real to snapshot).
        (wt / "src" / "wip_crlf.py").write_bytes(b"line one\r\nline two\r\n")
        assert _run(["git", "status", "--porcelain"], wt).stdout.strip() != ""

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.wip_committed is False

        wt_log = _run(["git", "log", "--oneline"], wt).stdout
        assert "wip: pre-land snapshot" not in wt_log


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


class TestDraftReferenceRewriteOnLand:
    """T-0811: land renumbers a finalized draft's structural id fields, but
    before this fix left Done-report PROSE citing the old draft id
    untouched, so TICK006's phantom-filing-claim gate reds main the
    moment the draft finalizes to a real id (recurred 3x this drive:
    T-0778/T-0797, T-0745/T-0764). A land whose own Done report cites its
    own (pre-finalize) draft id must come out with that reference rewritten
    to the final id, and zero `T-draft-` ids left anywhere in the ledger."""

    def test_land_rewrites_own_draft_id_reference_in_done_report(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-k", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Self-citing draft work", scope=("src/self.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "self.py").write_text("# self-citing draft work\n")

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nevidence attached\n"
                    + f"Filed: {primary_id} (scope-cut note filed against self)\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "self-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        report = result.danger_ok
        final_id = report.final_id
        assert final_id != primary_id

        landed = load_all(repo)
        assert landed.is_ok
        landed_map = landed.danger_ok
        assert primary_id not in landed_map

        final_ticket = landed_map[final_id]
        assert primary_id not in final_ticket.body, (
            "stale draft-id reference survived in the landed Done report"
        )
        assert f"Filed: {final_id}" in final_ticket.body

        ledger_text = ledger_path(repo).read_text(encoding="utf-8")
        assert "T-draft-" not in ledger_text, (
            "a T-draft- id survived somewhere in the landed ledger text"
        )

    def test_land_rewrites_strata_waive_clause_draft_id_reference(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812: extends the T-0811 body-prose rewrite to a `design/*.
        # strata` `waive` clause citing the SAME draft id being finalized
        # -- the original T-draft-8cd37914 incident class WAIVE007's
        # T-draft-* exemption otherwise leaves dangling forever.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-strata", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Strata-citing draft work", scope=("src/strata_ref.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "strata_ref.py").write_text("# strata-citing draft work\n")

        design_dir = wt / "design"
        design_dir.mkdir(parents=True, exist_ok=True)
        (design_dir / "waivers.strata").write_text(
            "component demo {\n"
            f'    waive "SYS203:demo" reason "draft waiver" ticket "{primary_id}";\n'
            "}\n"
        )

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "strata-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        strata_text = (repo / "design" / "waivers.strata").read_text(encoding="utf-8")
        assert primary_id not in strata_text, (
            "stale draft-id reference survived in the landed .strata waive clause"
        )
        assert f'ticket "{final_id}"' in strata_text

    def test_land_rewrites_frob_waive_comment_draft_id_reference(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812: same rewrite, source `frob:waive ... ticket=` comment
        # channel rather than `.strata`.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-waivecomment", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Comment-citing draft work", scope=("src/waive_ref.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "waive_ref.py").write_text(
            "x = 1  # noqa: E501\n"
            f'# frob:waive DEMO001 reason="draft waiver" ticket={primary_id}\n'
        )

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nevidence attached\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "comment-citing draft work")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        comment_text = (repo / "src" / "waive_ref.py").read_text(encoding="utf-8")
        assert primary_id not in comment_text, (
            "stale draft-id reference survived in the landed frob:waive comment"
        )
        assert f"ticket={final_id}" in comment_text

    def test_land_leaves_unrelated_draft_id_reference_untouched(
        self, repo: Path
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::land kind="unit"
        # T-0812 (reviewer follow-up on T-0811): the rewrite must be
        # per-id-keyed against the actual old->new mapping, not a blanket
        # "strip every T-draft- token" pass -- an UNRELATED draft id
        # mentioned in ledger prose (one that is not itself being
        # finalized by this land) must survive verbatim. Kept as its own
        # test since planting an unrelated draft id conflicts with the
        # existing blanket "zero T-draft- ids left in the ledger"
        # assertion in test_land_rewrites_own_draft_id_reference_in_done_report.
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-unrelated", str(wt)], repo)

        primary = new_ticket(
            wt, _spec("Primary work", scope=("src/unrelated_primary.py",))
        )
        assert primary.is_ok
        primary_id = primary.danger_ok.id
        assert primary_id.startswith("T-draft-")
        (wt / "src" / "unrelated_primary.py").write_text("# primary work\n")

        unrelated_draft_id = "T-draft-deadbeef"
        assert unrelated_draft_id != primary_id

        assert transition(wt, primary_id, TicketState.PLANNED).is_ok
        assert transition(wt, primary_id, TicketState.IN_PROGRESS).is_ok
        loaded = load_all(wt)
        ticket = loaded.danger_ok[primary_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": (
                    ticket.body
                    + "\n## Done report\n\nevidence attached\n"
                    + f"Note: unrelated to {unrelated_draft_id}, not landing it\n"
                ),
            }
        )
        assert write_ticket(wt, ticket).is_ok

        _commit_all(wt, "primary work citing an unrelated draft id in prose")

        result = land(repo, primary_id, wt, dry_run=False)
        assert result.is_ok, result.err
        final_id = result.danger_ok.final_id
        assert final_id != primary_id

        landed = load_all(repo)
        assert landed.is_ok
        final_ticket = landed.danger_ok[final_id]
        assert unrelated_draft_id in final_ticket.body, (
            "unrelated draft id in prose was rewritten/stripped -- the "
            "substitution must be scoped to this land's own old->new "
            "mapping, not a blanket T-draft- removal"
        )


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


# frob:ticket T-0793
class TestUvLockSync:
    """T-0793: land's release-bump step re-syncs `uv.lock` in the SAME
    commit as a real version bump, and the DirtyMain check tolerates (and
    auto-restores) a `uv.lock` whose only drift is the frob-version line
    flapping from a prior `uv run`/`uv lock` against an already-bumped
    pyproject.toml."""

    def test_bump_then_lock_synced_in_commit(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_bump_then_lock_synced_in_commit  # noqa: E501
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.1.0"\n'
        )
        _commit_all(repo, "add pyproject")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lock", str(wt)], repo)
        created = new_ticket(wt, _spec("Bump with lock", scope=("src/locked.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "locked.py").write_text("# locked\n")
        _commit_all(wt, "add locked.py")

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                (kwargs["cwd"] / "uv.lock").write_text(
                    '[[package]]\nname = "frob"\nversion = "1.2.3"\n'
                )
                return Ok(
                    ProcResult(argv=tuple(argv), returncode=0, stdout="", stderr="")
                )
            return run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_mod, "run_argv", _fake_run_argv)

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "1.2.3"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_ok, result.err
        assert result.danger_ok.release_bumped_to == "1.2.3"
        assert (repo / "uv.lock").read_text().count('version = "1.2.3"') == 1
        # uv.lock landed in the SAME commit as the bump, not left dirty.
        assert _status_ignoring_frob(repo) == ""
        committed_files = _run(
            ["git", "show", "--name-only", "--pretty=format:", "HEAD"], repo
        ).stdout.split()
        assert "uv.lock" in committed_files

    def test_dirty_lock_version_line_only_does_not_refuse(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_version_line_only_does_not_refuse  # noqa: E501
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockdirty", str(wt)], repo)
        created = new_ticket(wt, _spec("Tolerate lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # Simulate the flap: only the frob version line in uv.lock changed,
        # nothing else in the tree is dirty.
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_ok, result.err
        # The drift was auto-restored back to the committed content.
        assert 'version = "0.1.0"' in (repo / "uv.lock").read_text()
        assert _status_ignoring_frob(repo) == ""

    def test_dirty_lock_with_other_change_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_with_other_change_still_refuses  # noqa: E501
        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.1.0"\nsource = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockplus", str(wt)], repo)
        created = new_ticket(wt, _spec("Real dirt"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        (repo / "uv.lock").write_text(
            '[[package]]\nname = "frob"\nversion = "0.2.0"\nsource = { editable = "." }\n'
        )
        (repo / "other.txt").write_text("real uncommitted change\n")

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain

    def test_dirty_lock_version_plus_other_line_still_refuses(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_dirty_lock_version_plus_other_line_still_refuses  # noqa: E501
        (repo / "uv.lock").write_text(
            "[[package]]\n"
            'name = "frob"\n'
            'version = "0.1.0"\n'
            'source = { editable = "." }\n'
        )
        _commit_all(repo, "add uv.lock")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockmixed", str(wt)], repo)
        created = new_ticket(wt, _spec("Mixed lock drift"))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        _commit_all(wt, "wip")

        # uv.lock is the SOLE dirty path, but its diff touches BOTH the
        # frob version line AND another line (a dependency hash flip,
        # here a changed `source` value) -- `_diff_is_frob_version_line_
        # only` must reject this shape (len(changed) != 2) so the
        # destructive auto-restore never fires on real lock content.
        dirty_content = (
            "[[package]]\n"
            'name = "frob"\n'
            'version = "0.2.0"\n'
            'source = { editable = "./elsewhere" }\n'
        )
        (repo / "uv.lock").write_text(dirty_content)

        result = land(repo, tid, wt, dry_run=True)
        assert result.is_err
        assert result.danger_err == LandError.DirtyMain
        # Not auto-restored: the dirty content is left exactly as written.
        assert (repo / "uv.lock").read_text() == dirty_content

    def test_lock_sync_spawn_failure_unwinds_squash(
        self, repo: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestUvLockSync.test_lock_sync_spawn_failure_unwinds_squash  # noqa: E501
        (repo / "pyproject.toml").write_text(
            '[project]\nname = "frob"\nversion = "0.1.0"\n'
        )
        _commit_all(repo, "add pyproject")

        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-lockfail", str(wt)], repo)
        created = new_ticket(
            wt, _spec("Bump with failing lock", scope=("src/failedlock.py",))
        )
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "failedlock.py").write_text("# failed lock\n")
        _commit_all(wt, "add failedlock.py")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        def _fake_run_argv(argv: Sequence[str], **kwargs: Any) -> Any:
            if tuple(argv) == ("uv", "lock"):
                return Ok(
                    ProcResult(
                        argv=tuple(argv),
                        returncode=1,
                        stdout="",
                        stderr="simulated uv lock failure",
                    )
                )
            return run_argv(argv, **kwargs)

        monkeypatch.setattr(_land_mod, "run_argv", _fake_run_argv)

        def bump_version(root: Path, ticket: Any, final_id: str) -> Any:
            (root / "pyproject.toml").write_text(
                '[project]\nname = "frob"\nversion = "1.2.3"\n'
            )
            _run(["git", "add", "pyproject.toml"], root)
            return Ok("1.2.3")

        result = land(repo, tid, wt, dry_run=False, bump_version=bump_version)
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert (
            _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == before_main_sha
        )
        assert _run(["git", "status", "--porcelain"], repo).stdout.strip() == ""


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
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_matching_claims_land_succeeds  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_divergent_test_count_refuses_land  # noqa: E501
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

    def test_divergent_gate_errors_refuses_land(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_divergent_gate_errors_refuses_land  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_lower_gate_error_count_than_claim_still_lands  # noqa: E501
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

    # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_masked_self_introduced_error_in_own_scope_still_refuses_via_identity  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_divergent_warning_or_waived_count_alone_still_lands  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_no_claims_section_skips_reverification  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_unmeasured_fresh_check_skips_gate_reverification_land_proceeds  # noqa: E501
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
        assert "-1" not in notices[0]

    def test_two_unmeasured_gate_claims_never_vacuously_match(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestClaimDivergencePostMerge.test_two_unmeasured_gate_claims_never_vacuously_match  # noqa: E501
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
        assert "-1" not in done.danger_ok.body
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
        # frob:tests tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_report_then_land_succeeds  # noqa: E501
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


# T-0828: the T-0731 `pre-commit` hook shape (`_FORBID_LAND_OWNED_FILES_
# SCRIPT` in `frob.scaffold.project`) refuses any commit that stages
# CHANGELOG.md unless `FROB_LAND_INTERNAL` is set in the child's env.
# Copied here (not imported) so the regression test exercises the same
# guard SHAPE a real scaffolded repo would install, without coupling this
# test to `frob.scaffold.project`'s internals -- scope is `_land.py`/this
# test file only.
_CHANGELOG_GUARD_HOOK = """#!/bin/sh
if [ -z "$FROB_LAND_INTERNAL" ]; then
    staged=$(git diff --cached --name-only)
    case "$staged" in
        *CHANGELOG.md*)
            echo "frob: refusing commit -- CHANGELOG.md is land-owned (T-0731)" >&2
            exit 1
            ;;
    esac
fi
exit 0
"""


def _install_changelog_guard_hook(repo: Path) -> None:
    """Install the T-0731-shaped `pre-commit` hook (real hooks dir, shared
    across every linked worktree of `repo`) that refuses a commit staging
    CHANGELOG.md unless `FROB_LAND_INTERNAL` is set -- the regression
    fixture for T-0828."""
    hooks_dir = Path(
        _run(["git", "rev-parse", "--git-common-dir"], repo).stdout.strip()
    )
    if not hooks_dir.is_absolute():
        hooks_dir = repo / hooks_dir
    hooks_dir = hooks_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-commit"
    hook_path.write_text(_CHANGELOG_GUARD_HOOK)
    hook_path.chmod(0o755)


class TestLandInternalEnvThroughHook:
    """T-0828: every land-internal git commit spawn (worktree wip
    snapshot, main-into-worktree merge, finalize/close, main-side
    squash-apply) must set `FROB_LAND_INTERNAL=1` in the child env or a
    scaffolded T-0731 land-owned-files `pre-commit` hook deadlocks the
    land the moment any of those commits stages CHANGELOG.md."""

    def test_land_through_changelog_guard_hook_succeeds(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandInternalEnvThroughHook.test_land_through_changelog_guard_hook_succeeds  # noqa: E501
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
        # frob:tests src/frob/tickets/_land.py::_land_internal_git_env kind="unit"
        os.environ.pop("FROB_LAND_INTERNAL", None)
        with _land_mod._land_internal_git_env():
            assert os.environ.get("FROB_LAND_INTERNAL") == "1"
        assert "FROB_LAND_INTERNAL" not in os.environ

        os.environ["FROB_LAND_INTERNAL"] = "prior-value"
        try:
            with _land_mod._land_internal_git_env():
                assert os.environ.get("FROB_LAND_INTERNAL") == "1"
            assert os.environ.get("FROB_LAND_INTERNAL") == "prior-value"
        finally:
            os.environ.pop("FROB_LAND_INTERNAL", None)


class TestGitFailureMessageCarriesStderr:
    """T-0828: a failed land-internal git spawn must surface its argv and
    stderr in the log line, not collapse to a bare `GitFailed`."""

    def test_describe_git_failure_includes_argv_and_stderr(self) -> None:
        # frob:tests src/frob/tickets/_land.py::_describe_git_failure kind="unit"
        argv = ["git", "-C", "/tmp/repo", "commit", "-m", "x"]
        failed = Ok(
            ProcResult(
                argv=tuple(argv),
                returncode=1,
                stdout="",
                stderr="frob: refusing commit -- CHANGELOG.md is land-owned (T-0731)",
            )
        )
        message = _land_mod._describe_git_failure(argv, failed)
        assert "git -C /tmp/repo commit -m x" in message
        assert "exit 1" in message
        assert "CHANGELOG.md is land-owned" in message

    def test_describe_git_failure_includes_spawn_error(self) -> None:
        # frob:tests src/frob/tickets/_land.py::_describe_git_failure kind="unit"
        argv = ["git", "-C", "/tmp/repo", "commit", "-m", "x"]
        message = _land_mod._describe_git_failure(argv, Err(GitError.GitFailed))
        assert "git -C /tmp/repo commit -m x" in message
        assert "spawn error" in message

    def test_wip_commit_failure_logs_stderr(
        self,
        repo: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/tickets/_land.py::_do_wip_commit kind="unit"
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

        from frob.tickets._models import Ticket

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
        # frob:tests tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_security_kind_error_finding_blocks  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_feature_kind_warn_finding_does_not_block  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_no_findings_is_ok  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestMutationEvidencePrecheck.test_skip_flag_bypasses_error_finding_but_still_logs  # noqa: E501
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


# frob:ticket T-0854
class TestLiveTrackerCitationPrecheck:
    """T-0854: `_check_live_tracker_citations` blocks land when a registry
    disposition or waiver still cites the landing ticket as its live
    tracker -- unit-level over the private helper (same posture as
    `TestMutationEvidencePrecheck` above), isolating the refusal decision
    from a full land() run."""

    def _ticket_t0900(self) -> Any:
        from frob.tickets._models import Ticket

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
        # frob:tests tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck.test_citations_found_blocks  # noqa: E501
        import frob.tickets._live_tracker as _live_tracker_mod

        monkeypatch.setattr(
            _live_tracker_mod,
            "live_tracker_citations",
            lambda *a, **k: ("docs/design/registry/patterns.yaml:3: deferred:T-0900",),
        )
        result = _land_mod._check_live_tracker_citations(
            tmp_path, self._ticket_t0900(), "main"
        )
        assert result.is_err
        assert result.danger_err == LandError.LiveTrackerCited

    def test_no_citations_is_ok(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLiveTrackerCitationPrecheck.test_no_citations_is_ok  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring.test_flag_parses_to_true  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestSkipMutationEvidenceCliWiring.test_flag_omitted_defaults_false  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceCliWiring.test_flag_parses_to_true  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceCliWiring.test_flag_omitted_defaults_false  # noqa: E501
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

        from frob.tickets._models import Ticket

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
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_error_severity_finding_returns_false  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_warn_only_severity_returns_true  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_no_findings_returns_none  # noqa: E501
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
        # frob:tests tests/test_ticket_land.py::TestCloseMutationEvidenceForTicket.test_unresolvable_branch_returns_none  # noqa: E501
        # tmp_path is NOT a git work tree -- current_branch(root) must
        # fail, and the whole check degrades to "skip", never a false
        # ERROR/OK verdict.
        from frob.app import ticket_runner

        result = ticket_runner._close_mutation_evidence_for_ticket(
            tmp_path, self._ticket()
        )
        assert result is None


# frob:ticket T-0844
class TestCloseFailureHintMutationEvidence:
    """T-0844 rework (reviewer REJECT): `_close_failure_hint`'s
    `EvidenceConfirmatoryOnly` branch is real, dedicated behavior (names
    the skip-flag remedy), not indistinguishable from the generic
    fallback message -- the exact `compare Eq swapped` mutant T-0755's
    self-check caught as surviving."""

    def test_confirmatory_only_hint_names_skip_flag_remedy(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseFailureHintMutationEvidence.test_confirmatory_only_hint_names_skip_flag_remedy  # noqa: E501
        from frob.app.ticket_runner import _close_failure_hint
        from frob.tickets._models import TicketError, TicketState

        hint = _close_failure_hint(
            "T-0900", TicketState.IN_PROGRESS, TicketError.EvidenceConfirmatoryOnly
        )
        assert "--skip-mutation-evidence" in hint
        assert "TEST016" in hint

    def test_other_error_does_not_name_skip_flag_remedy(self) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseFailureHintMutationEvidence.test_other_error_does_not_name_skip_flag_remedy  # noqa: E501
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
        from frob.tickets._store import _serialize_ticket

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
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass.test_skip_flag_bypasses_error_verdict  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        self._write_closeable_security_ticket(tmp_path)
        monkeypatch.setattr(
            ticket_runner,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket: False,
        )
        monkeypatch.setattr(
            ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        cfg = AppConfig(ticket_id="T-0900", ticket_close_skip_mutation_evidence=True)
        ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.DONE

    def test_no_skip_flag_refuses_on_error_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestCloseSkipMutationEvidenceBypass.test_no_skip_flag_refuses_on_error_verdict  # noqa: E501
        from frob.app import ticket_runner
        from frob.app.config import AppConfig
        from frob.tickets import TicketState, load_all

        self._write_closeable_security_ticket(tmp_path)
        monkeypatch.setattr(
            ticket_runner,
            "_close_mutation_evidence_for_ticket",
            lambda root, ticket: False,
        )
        monkeypatch.setattr(
            ticket_runner, "_covers_scope_for_ticket", lambda root, ticket: None
        )
        cfg = AppConfig(ticket_id="T-0900", ticket_close_skip_mutation_evidence=False)
        with pytest.raises(SystemExit):
            ticket_runner._close(tmp_path, cfg)
        loaded = load_all(tmp_path)
        assert loaded.is_ok
        assert loaded.danger_ok["T-0900"].state == TicketState.IN_PROGRESS


# frob:ticket T-0907
class TestVerifiedResetRoot:
    """T-0907: `_verified_reset_root` replaces every bare `git reset --hard`
    unwind in `land`'s squash-apply stage. A bare reset resolves its target
    from whatever `HEAD` happens to be AT RESET TIME -- the real incident
    this closes was a killed land whose unwind reset main to a stale tip
    ~60 commits behind, because at reset time root's `HEAD` had already
    (somehow) drifted from what the run started with. `_verified_reset_root`
    resets to an EXPLICIT sha captured at run start instead, and refuses
    loudly -- performing NO reset at all -- if root's current tip no longer
    matches it."""

    def test_resets_to_the_explicit_pre_land_tip_when_current_matches(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestVerifiedResetRoot.test_resets_to_the_explicit_pre_land_tip_when_current_matches  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "scratch.txt").write_text("staged but never committed\n")
        _run(["git", "add", "scratch.txt"], repo)

        result = _land_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_ok, result.err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""

    def test_refuses_and_does_not_reset_when_current_tip_has_drifted(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestVerifiedResetRoot.test_refuses_and_does_not_reset_when_current_tip_has_drifted  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        (repo / "another.txt").write_text("a real commit made after pre was captured\n")
        _commit_all(repo, "advance main past the recorded pre-land tip")
        drifted_tip = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert drifted_tip != pre

        result = _land_mod._verified_reset_root(repo, pre, "T-TEST")
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # NOT reset -- the drifted commit must still be there, untouched.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted_tip


# frob:ticket T-0907
class TestLandRepairMarker:
    """T-0907: `_repair_stale_land_marker` reconciles a crashed land's
    leftover land-repair marker at the start of the NEXT `land()` call
    against the same root/ticket."""

    def test_no_marker_is_a_silent_no_op(self, repo: Path) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_no_marker_is_a_silent_no_op  # noqa: E501
        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_ok

    def test_repair_resets_root_when_current_tip_matches_the_marker(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_resets_root_when_current_tip_matches_the_marker  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_land_repair_marker(repo, "T-9999", pre)
        (repo / "leftover.txt").write_text("leftover staged squash content\n")
        _run(["git", "add", "leftover.txt"], repo)

        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_ok, result.err
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == pre
        assert _status_ignoring_frob(repo) == ""
        marker = _land_mod._land_repair_marker_path(repo, "T-9999")
        assert not marker.exists()

    def test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestLandRepairMarker.test_repair_refuses_loudly_when_current_tip_has_drifted_from_the_marker  # noqa: E501
        pre = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        _land_mod._write_land_repair_marker(repo, "T-9999", pre)
        (repo / "advance.txt").write_text("a real commit landed since the marker\n")
        _commit_all(repo, "advance main past the marker's recorded tip")
        drifted = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()

        result = _land_mod._repair_stale_land_marker(repo)
        assert result.is_err
        assert result.danger_err == LandError.GitFailed
        # refuses WITHOUT resetting -- the drifted commit must survive, and
        # the marker must be left in place for a human to inspect.
        assert _run(["git", "rev-parse", "HEAD"], repo).stdout.strip() == drifted
        marker = _land_mod._land_repair_marker_path(repo, "T-9999")
        assert marker.exists()


def _t0907_child_land(
    root: Path, ticket_id: str, worktree: Path, ready_path: Path
) -> None:
    """Multiprocessing target (module-level so `fork` can spawn it, T-0907):
    monkeypatches `frob.tickets._land.run_argv` (this CHILD process's own
    copy of the module, `fork` gives every child an independent
    copy-on-write memory image) so that once `land()`'s squash-apply merge
    onto `root` actually runs, it signals readiness (`ready_path`) and then
    sleeps well past however long the parent needs to `SIGKILL` this
    process -- reproducing "killed mid-staging" deterministically instead
    of relying on timing luck against a real 580s coordinator timeout."""
    from typani.result import Result

    import frob.tickets._land as land_mod

    real_run_argv = land_mod.run_argv

    def _patched(
        argv: Sequence[str], *, cwd: Path | None = None, timeout_s: int | float = 30.0
    ) -> Result[ProcResult, GitError]:
        result = real_run_argv(argv, cwd=cwd, timeout_s=timeout_s)
        if "merge" in argv and "--squash" in argv:
            ready_path.write_text("ready\n")
            time.sleep(30)
        return result

    setattr(land_mod, "run_argv", _patched)  # noqa: B010
    land_mod.land(root, ticket_id, worktree, dry_run=False)


# frob:ticket T-0907
class TestSigkillMidStaging:
    """T-0907's own regression lock: a real `SIGKILL` (uncatchable by any
    in-process signal handler, unlike SIGTERM) delivered while `land()` is
    mid-squash-apply onto root must leave root's tip completely unchanged,
    and the crash must be repairable by the next `land()` call for the same
    ticket -- the incident this ticket exists to close was the opposite: a
    killed land's own unwind reset main to a stale tip ~60 commits behind."""

    def test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry(
        self, repo: Path
    ) -> None:
        # frob:tests tests/test_ticket_land.py::TestSigkillMidStaging.test_sigkill_mid_squash_leaves_tip_unchanged_and_repairs_on_retry  # noqa: E501
        wt = repo.parent / "wt"
        _run(["git", "worktree", "add", "-b", "feature-kill", str(wt)], repo)
        created = new_ticket(wt, _spec("Add killable", scope=("src/killable.py",)))
        assert created.is_ok
        tid = created.danger_ok.id
        _make_closeable(wt, tid)
        (wt / "src" / "killable.py").write_text("# new file\n")
        _commit_all(wt, "add killable")

        before_main_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        ready_path = repo.parent / "ready.flag"

        ctx = multiprocessing.get_context("fork")
        proc = ctx.Process(target=_t0907_child_land, args=(repo, tid, wt, ready_path))
        proc.start()
        deadline = time.monotonic() + 20
        while not ready_path.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert ready_path.exists(), "child land() never reached the squash-apply step"
        assert proc.pid is not None
        os.kill(proc.pid, signal.SIGKILL)
        proc.join(timeout=15)
        assert not proc.is_alive()

        # The kill must not have moved root's tip AT ALL.
        after_kill_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_kill_sha == before_main_sha

        # A land-repair marker must survive the kill, recording exactly
        # this run's pre-land tip.
        marker_dir = repo / ".frob" / "land-repair"
        marker_files = list(marker_dir.glob("*.json"))
        assert len(marker_files) == 1, marker_files

        # The killed run already finalized/renumbered the draft id (and
        # closed it) in the worktree before its own crash -- exactly the
        # T-0795 retry shape (TestLandRetryAfterFinalizeThenFail above):
        # the retry addresses the ticket by its now-finalized id.
        wt_tickets = load_all(wt).danger_ok
        final_id = next(i for i, t in wt_tickets.items() if t.state == TicketState.DONE)

        # The next `land()` call for the same ticket reconciles the marker
        # (root's tip still matches it -- the crash happened before any
        # commit landed on root) and actually lands.
        result = land(repo, final_id, wt, dry_run=False)
        assert result.is_ok, result.err
        assert not marker_files[0].exists()
        assert (repo / "src" / "killable.py").exists()
        after_retry_sha = _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
        assert after_retry_sha != before_main_sha
        assert _status_ignoring_frob(repo) == ""
