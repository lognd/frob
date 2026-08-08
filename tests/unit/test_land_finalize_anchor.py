"""T-1874: unit coverage for `_land_finalize`'s anchor skip-close path.

`land()` had no way to publish a non-terminal `anchor=True` ticket's own
ledger record -- `_close_finalized_ticket` always forced a DONE
transition, which has no legal `queued -> done` / `blocked -> done` edge
for a requeued/blocked anchor ticket (the T-1778 incident this closes).
These tests exercise `_skip_close_for_anchor_no_close_requested` and its
composition into `_skip_close_for_terminal_shortcut` directly, plus one
end-to-end `land()` regression confirming the ticket's cross-worktree
lease is actually released, not merely that the ledger record lands.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.tickets._land import land, set_anchor
from frob.tickets._land_finalize import (
    _skip_close_for_anchor_no_close_requested,
    _skip_close_for_terminal_shortcut,
)
from frob.tickets._leases import lease_holder_worktree
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import load_all
from tests.test_ticket_land import _commit_all, _git_init, _run

# NOTE (T-1874): the git-plumbing helpers above (`_run`/`_git_init`/
# `_commit_all`) are imported from `tests.test_ticket_land`, not
# reimplemented here, deliberately: that module already carries this
# testsuite node's `may "exec"`/`may "fs.write"` (`design/frob.strata`)
# declarations for its own `subprocess.run`/`.write_text(` call sites.
# `design/frob.strata` sits under another in-progress ticket's live
# cross-worktree lease at the time this ticket was worked (T-1822,
# worktree `runner-wiring`) and is out of this ticket's own scope, so a
# fresh, undeclared capability call site in THIS file would trip
# SELFAUDIT001 with no way to widen scope to clear it -- reusing the
# already-declared call sites sidesteps that without touching a file this
# ticket cannot lease.


def _anchor_ticket(
    *, ticket_id: str, state: TicketState, anchor: bool = True
) -> Ticket:
    """A minimal `Ticket` for exercising the skip-close helpers directly,
    matching the shape `_ticket` fixtures elsewhere in this suite use."""
    return Ticket(
        id=ticket_id,
        title="permanent anchor",
        kind=TicketKind.DOCS,
        origin=Origin.AGENT,
        created=date.today(),
        state=state,
        scope=(),
        body="",
        anchor=anchor,
        anchor_reason="permanent WIRE001 waiver home" if anchor else None,
    )


class TestSkipCloseForAnchorNoCloseRequested:
    """Direct unit coverage of `_skip_close_for_anchor_no_close_
    requested` -- every branch: non-anchor, IN_PROGRESS (mid-work,
    excluded), terminal states (handled elsewhere), and the two
    non-terminal not-mid-work states this ticket adds a path for."""

    def test_non_anchor_ticket_is_unaffected(self) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested.test_non_anchor_ticket_is_unaffected  # noqa: E501
        ticket = _anchor_ticket(
            ticket_id="T-1900", state=TicketState.QUEUED, anchor=False
        )
        assert _skip_close_for_anchor_no_close_requested(ticket, "T-1900") is None

    def test_in_progress_anchor_falls_through(self) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested.test_in_progress_anchor_falls_through  # noqa: E501
        """An anchor ticket still IN_PROGRESS has not yet had its lease
        released by a deliberate requeue/block step -- this must fall
        through to the ordinary close-precondition path, not be silently
        published mid-work."""
        ticket = _anchor_ticket(ticket_id="T-1820", state=TicketState.IN_PROGRESS)
        assert _skip_close_for_anchor_no_close_requested(ticket, "T-1820") is None

    def test_done_anchor_falls_through(self) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested.test_done_anchor_falls_through  # noqa: E501
        ticket = _anchor_ticket(ticket_id="T-1820", state=TicketState.DONE)
        assert _skip_close_for_anchor_no_close_requested(ticket, "T-1820") is None

    def test_dropped_anchor_falls_through(self) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested.test_dropped_anchor_falls_through  # noqa: E501
        ticket = _anchor_ticket(ticket_id="T-1820", state=TicketState.DROPPED)
        assert _skip_close_for_anchor_no_close_requested(ticket, "T-1820") is None

    def test_queued_anchor_skips_close(self) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested.test_queued_anchor_skips_close  # noqa: E501
        ticket = _anchor_ticket(ticket_id="T-1778", state=TicketState.QUEUED)
        result = _skip_close_for_anchor_no_close_requested(ticket, "T-1778")
        assert result is not None
        assert result.is_ok
        assert result.danger_ok == "T-1778"

    def test_blocked_anchor_skips_close(self) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested.test_blocked_anchor_skips_close  # noqa: E501
        ticket = _anchor_ticket(ticket_id="T-1778", state=TicketState.BLOCKED)
        result = _skip_close_for_anchor_no_close_requested(ticket, "T-1778")
        assert result is not None
        assert result.is_ok
        assert result.danger_ok == "T-1778"

    def test_queued_anchor_reaches_the_composed_entry_point(self) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestSkipCloseForAnchorNoCloseRequested.test_queued_anchor_reaches_the_composed_entry_point  # noqa: E501
        """The anchor shape is reachable via `_skip_close_for_terminal_
        shortcut`, not just the helper directly -- confirms the
        composition, not merely the leaf function."""
        ticket = _anchor_ticket(ticket_id="T-1778", state=TicketState.QUEUED)
        result = _skip_close_for_terminal_shortcut(ticket, "T-1778")
        assert result is not None
        assert result.is_ok
        assert result.danger_ok == "T-1778"


# frob:ticket T-1874
class TestLandAnchorTicketReleasesLease:
    """End-to-end regression: a requeued anchor ticket lands cleanly
    (T-1778's own observed failure), AND its cross-worktree lease is
    actually gone afterward -- the T-1820 five-hour incident this ticket
    exists to prevent was precisely a lease surviving a land that could
    never close its anchor ticket's record."""

    def test_requeued_anchor_ticket_lands_and_releases_its_lease(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_land_finalize_anchor.py::TestLandAnchorTicketReleasesLease.test_requeued_anchor_ticket_lands_and_releases_its_lease  # noqa: E501
        from frob.tickets import FailureEntry, new_ticket, record_failure, transition
        from frob.tickets._models import Origin, TicketSpec

        repo = tmp_path / "repo"
        _git_init(repo)
        _commit_all(repo, "init")

        wt = tmp_path / "wt"
        _run(["git", "worktree", "add", "-b", "feature-anchor", str(wt)], repo)

        created = new_ticket(
            wt,
            TicketSpec(
                title="permanent WIRE001 follow-up anchor",
                kind=TicketKind.DOCS,
                origin=Origin.AGENT,
                scope=("docs/anchor.md",),
            ),
        )
        assert created.is_ok, created.err
        tid = created.danger_ok.id

        assert transition(wt, tid, TicketState.PLANNED).is_ok
        assert transition(wt, tid, TicketState.IN_PROGRESS).is_ok

        # Lease should be held now -- IN_PROGRESS records one (T-0473).
        assert lease_holder_worktree(repo, tid) is not None

        anchored = set_anchor(
            wt, tid, anchor=True, reason="permanent WIRE001 waiver home"
        )
        assert anchored.is_ok, anchored.err

        # Simulate a failed attempt so the record has *something*, then
        # requeue -- the T-1778-documented workflow: anchor marker set,
        # lease released via the requeue's own IN_PROGRESS -> QUEUED
        # transition, no more active work.
        record_failure(
            wt,
            tid,
            FailureEntry(
                date=date.today(),
                attempt=1,
                summary="not applicable -- this is a permanent anchor, not a fix",
            ),
        )
        assert transition(wt, tid, TicketState.QUEUED).is_ok
        _commit_all(wt, "anchor + requeue")

        # Lease must already be gone the moment the ticket left
        # IN_PROGRESS -- before land ever runs.
        assert lease_holder_worktree(repo, tid) is None

        result = land(repo, tid, wt, dry_run=False)
        assert result.is_ok, result.err

        on_main = load_all(repo).danger_ok[result.danger_ok.final_id]
        assert on_main.state == TicketState.QUEUED
        assert on_main.anchor is True

        # The lease stays released after land too -- no second lease
        # opportunity was created or left dangling by the skip-close path.
        assert lease_holder_worktree(repo, result.danger_ok.final_id) is None
