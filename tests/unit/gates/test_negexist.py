"""Tests for `frob.gates._negexist` (T-1229): NEGEXIST001's unbound and
stale negative-existence-claim detection, plus `frob.graph.dsl`'s
`frob:until`/heuristic-claim markdown-anchor parsing that feeds it."""

from __future__ import annotations

from datetime import date

from frob.gates import GraphSnapshot
from frob.gates._negexist import negexist001_gate
from frob.graph._models import Edge, EdgeKind
from frob.graph.dsl import markdown_anchors
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _test_queue(ticket_id: str, state: TicketState) -> TicketQueue:
    """Test helper: a `TicketQueue` with a single ticket at `state`."""
    return TicketQueue(
        tickets={
            ticket_id: Ticket(
                id=ticket_id,
                title="Sample",
                state=state,
                kind=TicketKind.FEATURE,
                origin=Origin.HUMAN,
                created=date(2026, 1, 1),
                scope=(),
                evidence=(),
                body="## Description\nx\n\n## Done report\ndone\n",
            )
        }
    )


def _test_snapshot(edges: tuple[Edge, ...]) -> GraphSnapshot:
    """Test helper: a minimal `GraphSnapshot` carrying only `edges`."""
    return GraphSnapshot(root=".", symbols={}, edges=edges)


class TestMarkdownAnchorsUntilAndClaimsAbsence:
    """`markdown_anchors`'s T-1229 additions: `frob:until` and the
    negative-existence phrase heuristic."""

    def test_until_directive_emits_until_edge(self) -> None:
        """`<!-- frob:until T-0042 -->` under a heading becomes an UNTIL
        edge whose target is the ticket id and src is the doc anchor."""
        text = "# Section\n<!-- frob:until T-0042 -->\n"
        edges = markdown_anchors("doc.md", text)
        until_edges = [e for e in edges if e.kind == EdgeKind.UNTIL]
        assert len(until_edges) == 1
        assert until_edges[0].target == "T-0042"
        assert until_edges[0].src == "doc.md#section"

    def test_negative_existence_phrase_emits_claims_absence_edge(self) -> None:
        """A "does not exist yet" line under a heading becomes a
        CLAIMS_ABSENCE edge bound to that heading's anchor."""
        text = "# Section\nThe web dashboard does not exist yet.\n"
        edges = markdown_anchors("doc.md", text)
        claims = [e for e in edges if e.kind == EdgeKind.CLAIMS_ABSENCE]
        assert len(claims) == 1
        assert claims[0].src == "doc.md#section"

    def test_not_yet_wired_phrase_is_also_detected(self) -> None:
        """The "not yet <verb>" phrasing variant is detected too, not just
        "does not exist yet"."""
        text = "# Section\nThe cache layer is not yet wired up.\n"
        edges = markdown_anchors("doc.md", text)
        claims = [e for e in edges if e.kind == EdgeKind.CLAIMS_ABSENCE]
        assert len(claims) == 1

    def test_directive_comment_line_itself_never_matches_the_heuristic(self) -> None:
        """A directive comment line is skipped by the heuristic scan even
        if its own text happens to contain a matching phrase (defense
        against a directive's surrounding markdown prose self-matching)."""
        text = "# Section\n<!-- frob:until T-0042 does not exist yet -->\n"
        edges = markdown_anchors("doc.md", text)
        claims = [e for e in edges if e.kind == EdgeKind.CLAIMS_ABSENCE]
        assert claims == []

    def test_plain_prose_with_no_matching_phrase_emits_nothing(self) -> None:
        """Ordinary prose with no negative-existence phrasing at all emits
        no CLAIMS_ABSENCE edge (the heuristic is narrow by design)."""
        text = "# Section\nThe web dashboard ships next quarter.\n"
        edges = markdown_anchors("doc.md", text)
        claims = [e for e in edges if e.kind == EdgeKind.CLAIMS_ABSENCE]
        assert claims == []


class TestNegexist001Gate:
    """`negexist001_gate`'s unbound/stale grouping over already-parsed
    edges (T-1229)."""

    def test_unbound_claim_is_flagged(self) -> None:
        """A CLAIMS_ABSENCE edge with no sibling UNTIL edge in the same
        anchor fires NEGEXIST001."""
        edges = (
            Edge(
                src="doc.md#section",
                kind=EdgeKind.CLAIMS_ABSENCE,
                target="does not exist yet",
                origin="doc.md:2",
            ),
        )
        violations = negexist001_gate(_test_snapshot(edges), TicketQueue(tickets={}))
        assert len(violations) == 1
        assert violations[0].rule == "NEGEXIST001"
        assert "no `frob:until" in violations[0].message

    def test_claim_bound_to_open_ticket_is_clean(self) -> None:
        """A CLAIMS_ABSENCE edge sharing its anchor with an UNTIL edge
        bound to a still-open ticket produces no violation."""
        edges = (
            Edge(
                src="doc.md#section",
                kind=EdgeKind.CLAIMS_ABSENCE,
                target="does not exist yet",
                origin="doc.md:2",
            ),
            Edge(
                src="doc.md#section",
                kind=EdgeKind.UNTIL,
                target="T-0042",
                origin="doc.md:3",
            ),
        )
        queue = _test_queue("T-0042", TicketState.QUEUED)
        assert negexist001_gate(_test_snapshot(edges), queue) == ()

    def test_claim_bound_to_closed_ticket_is_stale(self) -> None:
        """An UNTIL edge naming an already-closed ticket is stale --
        NEGEXIST001 still fires even though the claim is technically
        bound."""
        edges = (
            Edge(
                src="doc.md#section",
                kind=EdgeKind.CLAIMS_ABSENCE,
                target="does not exist yet",
                origin="doc.md:2",
            ),
            Edge(
                src="doc.md#section",
                kind=EdgeKind.UNTIL,
                target="T-0042",
                origin="doc.md:3",
            ),
        )
        queue = _test_queue("T-0042", TicketState.DONE)
        violations = negexist001_gate(_test_snapshot(edges), queue)
        assert len(violations) == 1
        assert "none is" in violations[0].message

    def test_claim_bound_to_missing_ticket_is_stale(self) -> None:
        """An UNTIL edge naming a ticket absent from the queue entirely is
        treated the same as a closed ticket -- stale, not silently clean."""
        edges = (
            Edge(
                src="doc.md#section",
                kind=EdgeKind.CLAIMS_ABSENCE,
                target="does not exist yet",
                origin="doc.md:2",
            ),
            Edge(
                src="doc.md#section",
                kind=EdgeKind.UNTIL,
                target="T-9999",
                origin="doc.md:3",
            ),
        )
        violations = negexist001_gate(_test_snapshot(edges), TicketQueue(tickets={}))
        assert len(violations) == 1

    def test_no_claims_at_all_is_clean(self) -> None:
        """No CLAIMS_ABSENCE edges in the snapshot: nothing to flag, even
        with an unrelated UNTIL edge present."""
        edges = (
            Edge(
                src="doc.md#section",
                kind=EdgeKind.UNTIL,
                target="T-0042",
                origin="doc.md:3",
            ),
        )
        assert negexist001_gate(_test_snapshot(edges), TicketQueue(tickets={})) == ()
