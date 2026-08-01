"""T-1279: real behavioral tests for `frob.gates._todo_fmt`'s TODO001/
TODO002 and FMT001 helpers that had no test coverage at all -- distinct
from `TestFmt001Gate`/existing TODO003 coverage already living in the
LEASED `tests/test_gates.py` (T-1323), which this file does not touch.
"""
# frob:ticket T-1279

from __future__ import annotations

from datetime import date

from frob.gates._models import Severity
from frob.gates._todo_fmt import (
    _fmt001_marker_entries,
    _fmt001_violations_for_runs,
    _todo001_bare_comment,
    _todo002_edges,
)
from frob.graph import Edge, EdgeKind, GraphSnapshot
from frob.lang._models import RawComment
from frob.tickets import Origin, Ticket, TicketKind, TicketQueue, TicketState


def _snapshot(edges: tuple[Edge, ...]) -> GraphSnapshot:
    """A minimal `GraphSnapshot` carrying only the edges a test needs."""
    return GraphSnapshot(root="/repo", symbols={}, edges=edges)


def _ticket(
    ticket_id: str = "T-0001", state: TicketState = TicketState.QUEUED
) -> Ticket:
    """A minimal valid `Ticket` for `TicketQueue` fixtures."""
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=state,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nx\n\n## Done report\ndone\n",
    )


class TestTodo002Edges:
    """`_todo_fmt._todo002_edges`: a `frob:todo` edge bound to a non-open
    (or missing) ticket."""

    def test_open_ticket_no_violation(self) -> None:
        """A `frob:todo` edge bound to a still-open ticket raises nothing."""
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.QUEUED)})
        edge = Edge(
            src="pkg/mod.py::func",
            kind=EdgeKind.TODO,
            target="T-0001",
            origin="pkg/mod.py:5",
        )
        assert _todo002_edges(_snapshot((edge,)), queue) == []

    def test_closed_ticket_fires_todo002(self) -> None:
        """A `frob:todo` edge bound to a DONE ticket fires TODO002 at the
        edge's own origin site."""
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        edge = Edge(
            src="pkg/mod.py::func",
            kind=EdgeKind.TODO,
            target="T-0001",
            origin="pkg/mod.py:9",
        )
        violations = _todo002_edges(_snapshot((edge,)), queue)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "TODO002"
        assert v.severity == Severity.WARN
        assert v.file == "pkg/mod.py"
        assert v.line == 9
        assert "T-0001" in v.message

    def test_missing_ticket_fires_todo002(self) -> None:
        """A `frob:todo` edge whose target ticket does not exist at all
        also fires TODO002 (missing is treated the same as closed)."""
        queue = TicketQueue(tickets={})
        edge = Edge(
            src="pkg/mod.py::func",
            kind=EdgeKind.TODO,
            target="T-9999",
            origin="pkg/mod.py:3",
        )
        violations = _todo002_edges(_snapshot((edge,)), queue)
        assert len(violations) == 1
        assert violations[0].rule == "TODO002"

    def test_non_todo_edges_are_ignored(self) -> None:
        """Edges of a different `EdgeKind` never contribute a TODO002
        finding, even if their target ticket is closed."""
        queue = TicketQueue(tickets={"T-0001": _ticket(state=TicketState.DONE)})
        edge = Edge(
            src="pkg/mod.py::func",
            kind=EdgeKind.TICKET,
            target="T-0001",
            origin="pkg/mod.py:3",
        )
        assert _todo002_edges(_snapshot((edge,)), queue) == []


class TestTodo001BareComment:
    """`_todo_fmt._todo001_bare_comment`: bare (non-`frob:`), untracked
    deferral-marker lines inside one parsed comment."""

    def test_bare_todo_fires(self) -> None:
        """A plain untracked deferral-marker comment fires TODO001 at its
        own physical line."""
        comment = RawComment(
            text="TODO: fix this later",
            span=(12, 12),
            enclosing=None,
            following=None,
        )
        violations = _todo001_bare_comment("pkg/mod.py", comment)
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "TODO001"
        assert v.severity == Severity.WARN
        assert v.file == "pkg/mod.py"
        assert v.line == 12

    def test_frob_prefixed_line_is_not_bare(self) -> None:
        """A `frob:todo T-1234` line is a tracked directive, not a bare
        deferral marker -- never flagged by TODO001 even though it
        contains no untracked marker token to trip the regex anyway."""
        comment = RawComment(
            text="frob:todo T-1234 remember to do this",
            span=(4, 4),
            enclosing=None,
            following=None,
        )
        assert _todo001_bare_comment("pkg/mod.py", comment) == []

    def test_multiline_comment_flags_only_todo_lines(self) -> None:
        """A multi-line comment block fires once per bare untracked
        deferral-marker physical line, at the correct offset line number,
        and never for a line with neither token."""
        comment = RawComment(
            text="first line, nothing here\nFIXME: broken\nlast line ok",
            span=(20, 22),
            enclosing=None,
            following=None,
        )
        violations = _todo001_bare_comment("pkg/mod.py", comment)
        assert len(violations) == 1
        assert violations[0].line == 21

    def test_frob_prefixed_line_inside_multiline_block_is_skipped(self) -> None:
        """Within a multi-line comment, a `frob:`-prefixed physical line is
        skipped even if a sibling line in the same comment is a bare
        deferral marker."""
        comment = RawComment(
            text="frob:waive TODO001 reason=x\nTODO: real one",
            span=(1, 2),
            enclosing=None,
            following=None,
        )
        violations = _todo001_bare_comment("pkg/mod.py", comment)
        assert len(violations) == 1
        assert violations[0].line == 2

    def test_no_todo_token_no_violation(self) -> None:
        """An ordinary comment with neither deferral-marker token raises
        nothing."""
        comment = RawComment(
            text="just an explanatory comment",
            span=(1, 1),
            enclosing=None,
            following=None,
        )
        assert _todo001_bare_comment("pkg/mod.py", comment) == []


class TestFmt001MarkerEntries:
    """`_todo_fmt._fmt001_marker_entries`: collecting comment-marker lines
    ahead of `fold_comment_runs`."""

    def test_collects_only_marker_lines(self) -> None:
        """Only lines starting (after leading whitespace) with `marker`
        are collected, with the marker (and one following space) stripped
        from the content."""
        lines = [
            "code line",
            "# frob:tests foo::bar",
            "    # frob:doc baz",
            "not a comment at all",
        ]
        entries = _fmt001_marker_entries(lines, "#")
        assert entries == [
            (1, "frob:tests foo::bar", "", 0),
            (2, "frob:doc baz", "", 0),
        ]

    def test_no_marker_lines_yields_empty(self) -> None:
        """A file with no comment-marker lines at all yields no entries."""
        assert _fmt001_marker_entries(["a", "b", "c"], "#") == []


class TestFmt001ViolationsForRuns:
    """`_todo_fmt._fmt001_violations_for_runs`: over-length `frob:`
    directive lines, diff-touch and non-`frob:`-run filtering."""

    def test_over_limit_touched_frob_line_fires(self) -> None:
        """A `frob:`-prefixed run whose physical line exceeds `limit` and
        is diff-touched fires FMT001 at that physical line."""
        long_line = "# " + "frob:tests " + "x" * 100
        lines = ["", long_line, ""]
        runs = [(long_line[2:], 1, "", 1)]
        violations = _fmt001_violations_for_runs(
            "pkg/mod.py", lines, runs, limit=40, touched={2}
        )
        assert len(violations) == 1
        v = violations[0]
        assert v.rule == "FMT001"
        assert v.severity == Severity.WARN
        assert v.line == 2

    def test_untouched_line_not_flagged(self) -> None:
        """The same over-length run is silent when its physical line is
        not in the diff's touched-line set."""
        long_line = "# " + "frob:tests " + "x" * 100
        lines = ["", long_line, ""]
        runs = [(long_line[2:], 1, "", 1)]
        violations = _fmt001_violations_for_runs(
            "pkg/mod.py", lines, runs, limit=40, touched={99}
        )
        assert violations == []

    def test_non_frob_run_not_flagged(self) -> None:
        """A folded comment run that does not start with `frob:` is never
        flagged, no matter its length or touch status."""
        long_line = "# " + "x" * 100
        lines = ["", long_line, ""]
        runs = [(long_line[2:], 1, "", 1)]
        violations = _fmt001_violations_for_runs(
            "pkg/mod.py", lines, runs, limit=40, touched={2}
        )
        assert violations == []

    def test_short_frob_line_not_flagged(self) -> None:
        """A `frob:`-prefixed run within the column limit is silent even
        when touched."""
        short_line = "# frob:ticket T-0001"
        lines = ["", short_line, ""]
        runs = [(short_line[2:], 1, "", 1)]
        violations = _fmt001_violations_for_runs(
            "pkg/mod.py", lines, runs, limit=40, touched={2}
        )
        assert violations == []
