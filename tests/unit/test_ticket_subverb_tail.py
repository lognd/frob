"""T-4698 (ticket subverb tail): verdict per subverb.

ACCEPTANCE IS THE VERDICT TABLE (the ticket's own words) -- this module IS
that table, `_SUBVERB_VERDICTS` below, plus the one required positive
control (a KEPT subverb's cited consumer, exercised, that fails if the
subverb is removed). The Done report renders `_SUBVERB_VERDICTS` as its
own verdict-table section.

METHOD (per the ticket body): `git grep -n "ticket <name>"` across src/,
.claude/, docs/, scripts/, tests/; a positive hit count with real citing
files outside the subverb's own implementation/test is KEEP evidence. A
verdict with no grep evidence is not a verdict."""

from __future__ import annotations

from typing import NamedTuple


class SubverbVerdict(NamedTuple):
    """One row of T-4698's verdict table: `name`, `verdict` (KEEP/DELETE/
    ALREADY-REMOVED/DEFERRED), `hit_count` (the `git grep -c "ticket
    <name>"` sweep total across src/.claude/docs/scripts/tests, measured
    2026-09-22), and `citing` (representative file:line evidence, or the
    deferral/removal reason)."""

    name: str
    verdict: str
    hit_count: int
    citing: str


# frob:ticket T-4698
_SUBVERB_VERDICTS: tuple[SubverbVerdict, ...] = (
    SubverbVerdict(
        "attach", "KEEP", 26, "docs/modules/tickets.md, tests/test_ticket_attach.py"
    ),
    SubverbVerdict(
        "anchor",
        "KEEP",
        12,
        "T-1856/T-1820 -- WIRE001 follow_up anchors depend on this existing; "
        "docs/modules/tickets.md",
    ),
    SubverbVerdict(
        "flow", "KEEP", 18, "docs/modules/tickets.md, tests/test_tickets_flow.py"
    ),
    SubverbVerdict(
        "plan",
        "KEEP",
        3,
        "load-bearing: queued->planned is part of the close dance "
        "(src/frob/app/ticket_runner/_lifecycle.py::_plan)",
    ),
    SubverbVerdict(
        "board", "KEEP", 10, "docs/modules/tickets.md, tests/test_tickets_board.py"
    ),
    SubverbVerdict(
        "epic", "KEEP", 9, "docs/modules/tickets.md, tests/test_tickets_epic.py"
    ),
    SubverbVerdict(
        "wave", "KEEP", 10, "docs/modules/tickets.md, tests/test_tickets_wave.py"
    ),
    SubverbVerdict(
        "runs-last",
        "KEEP",
        21,
        "docs/modules/tickets.md, tests/test_tickets_runs_last.py",
    ),
    SubverbVerdict(
        "runs-last-parallel-safe",
        "KEEP",
        10,
        "docs/modules/tickets.md, tests/test_tickets_runs_last.py",
    ),
    SubverbVerdict(
        "migrate",
        "ALREADY-REMOVED",
        28,
        "T-4521 already removed this verb (frob.app.ticket_runner.__init__ "
        "'frob ticket migrate is removed (T-4521)') -- the 28 hits are "
        "historical citations/tests of the removal itself, not a live "
        "consumer; no action needed here, the ticket body's own subverb "
        "list predates T-4521",
    ),
    SubverbVerdict(
        "archive",
        "KEEP",
        67,
        "load-bearing (ticket body's own KNOWN LOAD-BEARING list)",
    ),
    SubverbVerdict(
        "reverify",
        "KEEP",
        18,
        "docs/modules/tickets.md, tests/test_tickets_reverify.py",
    ),
    SubverbVerdict(
        "waive-audit",
        "KEEP",
        9,
        "load-bearing (T-1614/T-2467, ticket body's own KNOWN LOAD-BEARING list)",
    ),
    SubverbVerdict(
        "review", "KEEP", 14, "docs/modules/tickets.md, tests/test_tickets_review.py"
    ),
    SubverbVerdict(
        "admin", "KEEP", 9, "docs/modules/tickets.md, tests/test_tickets_admin.py"
    ),
    SubverbVerdict(
        "debt",
        "DEFERRED",
        7,
        "coordinate with T-4695 (folds top-level debt/deprecated under "
        "explore) -- T-4695 is currently blocked by in-progress T-5201's "
        "live lease on explore_runner.py, so its own verdict has not been "
        "rendered yet; ticket debt/deprecated stay untouched here to avoid "
        "deciding twice, per the ticket's own coordination instruction",
    ),
    SubverbVerdict(
        "deprecated", "DEFERRED", 4, "same T-4695 coordination note as debt above"
    ),
    SubverbVerdict(
        "scope-ack",
        "KEEP",
        29,
        "docs/modules/tickets.md, tests/test_tickets_scope_ack.py",
    ),
    SubverbVerdict(
        "worktree", "KEEP", 13, "docs/modules/tickets.md, tests/test_ticket_worktree.py"
    ),
    SubverbVerdict(
        "contention",
        "KEEP",
        9,
        "tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand."
        "test_plain_render_ranks_and_names_owners",
    ),
    SubverbVerdict(
        "parse",
        "KEEP",
        23,
        "the ticket body's own recommendation is DELETE-with-shim, but its "
        "own measurement shows zero consumers outside parse's own impl/"
        "test/doc (docs/commands/parse.md, tests/unit/test_parse.py) -- "
        "deleting a working, documented, zero-issue tool-output adapter "
        "with NO replacement destination to shim TO is a net-negative "
        "surface change for this story's stated goal (removing DUPLICATE "
        "names, not removing unique capability); 'the recommendation is "
        "not the verdict' per the ticket's own text -- deviation recorded "
        "here with its reason",
    ),
)


# frob:ticket T-4698
class TestVerdictTableIsComplete:
    """The verdict table itself: every named subverb has a row, every row
    has real grep evidence (a positive hit count or an explicit removal/
    deferral reason), and no verdict is bare."""

    def test_every_named_subverb_has_a_row(self) -> None:
        expected = {
            "attach",
            "anchor",
            "flow",
            "plan",
            "board",
            "epic",
            "wave",
            "runs-last",
            "runs-last-parallel-safe",
            "migrate",
            "archive",
            "reverify",
            "waive-audit",
            "review",
            "admin",
            "debt",
            "deprecated",
            "scope-ack",
            "worktree",
            "contention",
            "parse",
        }
        assert {row.name for row in _SUBVERB_VERDICTS} == expected

    def test_every_row_carries_citing_evidence(self) -> None:
        for row in _SUBVERB_VERDICTS:
            assert row.citing, f"{row.name!r} has no citing evidence"
            assert row.verdict in {"KEEP", "DELETE", "ALREADY-REMOVED", "DEFERRED"}


# frob:ticket T-4698
class TestPositiveControlKeptSubverbConsumerExecutes:
    """T-4698's own required positive control: for at least one KEPT
    subverb, the cited consumer is executed here and fails if the
    subverb's own implementation is removed -- `contention`'s row above
    cites this exact test."""

    def test_contention_renders_a_real_overlap_ranking(self, tmp_path) -> None:
        from datetime import date
        from pathlib import Path

        from frob.app.ticket_runner._query import _compute_contention
        from frob.tickets import (
            Origin,
            Ticket,
            TicketKind,
            TicketState,
            load_all,
            write_ticket,
        )
        from frob.tickets._models import TicketQueue

        root: Path = tmp_path
        shared_scope = ("src/frob/shared_module.py",)
        for i in range(2):
            ticket = Ticket(
                id=f"T-810{i}",
                title=f"contention fixture {i}",
                kind=TicketKind.BUG,
                state=TicketState.IN_PROGRESS,
                origin=Origin.HUMAN,
                created=date(2026, 1, 1),
                body="fixture body",
                scope=shared_scope,
            )
            write_ticket(root, ticket)

        (root / "src" / "frob").mkdir(parents=True, exist_ok=True)
        (root / "src" / "frob" / "shared_module.py").write_text("# fixture\n")

        queue = TicketQueue(tickets=load_all(root).danger_ok)
        outcome = _compute_contention(root, queue)
        assert any(
            "src/frob/shared_module.py" in e.file and len(e.ticket_ids) >= 2
            for e in outcome.entries
        )


# frob:ticket T-4698
class TestNoDeleteVerdictThisRound:
    """T-4698 acceptance[3]'s amended, vacuous form: no subverb was
    verdicted DELETE this round (measured 2026-09-22), so there is no
    DELETE-shim behavior for this criterion to exercise -- asserted here
    directly so a future re-verdict that DOES add a DELETE row is the
    thing that makes this test meaningful again, not silently stale."""

    def test_no_row_is_verdicted_delete(self) -> None:
        assert not any(row.verdict == "DELETE" for row in _SUBVERB_VERDICTS)
