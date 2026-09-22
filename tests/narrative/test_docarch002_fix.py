"""`fix_docarch002_narrative_move` (T-4694): the Tier-A auto-fix that
registers `frob narrative move`'s own engine as DOCARCH002 check 2's
`frob check --fix` handler.

Each test is a GIVEN/WHEN/THEN off T-4694's own acceptance criteria and
its POSITIVE/NEGATIVE CONTROL.
"""

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.gates._fix_engine import fix_docarch002_narrative_move
from frob.graph import build_graph
from frob.tickets import load_queue
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import _serialize_ticket


def _git_init(root: Path) -> None:
    """A minimal git repo, tracked-file discovery's own prerequisite
    (`frob.gates._tracked_files.tracked_files` reads `git ls-files`)."""
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "t@t.t"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=root, check=True)


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs -- same shape
    `test_bulk.py`'s own helper uses."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _make_ticket(ticket_id: str) -> Ticket:
    """A minimal queued `Ticket`, matching `test_bulk.py`'s own
    `_make_ticket` shape."""
    return Ticket(
        id=ticket_id,
        title="Sample",
        state=TicketState.QUEUED,
        kind=TicketKind.FEATURE,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=(),
        evidence=(),
        attachments=(),
        body="## Description\nsomething\n",
    )


def _write_active_ticket(root: Path, ticket_id: str) -> None:
    """Create `tickets/<id>/ticket.md` (v2, active) directly on disk."""
    d = root / "tickets" / ticket_id
    d.mkdir(parents=True)
    (d / "ticket.md").write_text(_serialize_ticket(_make_ticket(ticket_id)))


def _write_archived_ticket(root: Path, ticket_id: str) -> None:
    """Create `tickets/archive/<id>/ticket.md` (v2, archived) directly on
    disk -- `set_body` must amend this path in place (T-2678)."""
    d = root / "tickets" / "archive" / ticket_id
    d.mkdir(parents=True)
    (d / "ticket.md").write_text(_serialize_ticket(_make_ticket(ticket_id)))


def _add_all(root: Path) -> None:
    """`git add -A` -- `tracked_files` only ever sees added/committed
    paths, matching the real `git ls-files` this handler scans."""
    subprocess.run(["git", "add", "-A"], cwd=root, check=True)


# frob:tests docs/commands/narrative.md#docarch002-check-2s-tier-a-auto-fix-t-4694
def test_docs_disclose_the_whole_block_move_limitation() -> None:
    """Acceptance [5]: given docs/commands/narrative.md, when this lands,
    THEN it states that --fix moves the WHOLE cited block and cannot
    make the load-bearing/archaeology split (T-2994 constraint 2)."""
    text = (
        Path(__file__).resolve().parents[2] / "docs" / "commands" / "narrative.md"
    ).read_text(encoding="utf-8")
    assert "DOCARCH002 check 2's Tier-A auto-fix" in text
    assert "always moves the WHOLE cited comment run" in text


def _snap(root: Path):  # noqa: ANN201
    """A `GraphSnapshot` for the handler's unused `snapshot` parameter --
    the handler itself never reads it (DOCARCH002 findings come from
    `scan_citation_shape`, not graph edges), but the call shape every
    other `TIER_A_HANDLERS` entry shares requires one."""
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


class TestFixDocarch002NarrativeMove:
    """`fix_docarch002_narrative_move`."""

    # frob:tests src/frob/gates/_fix_engine.py::fix_docarch002_narrative_move
    def test_positive_control_moves_prose_and_leaves_pointer(
        self, tmp_path: Path
    ) -> None:
        """GIVEN a fixture with a '# T-1234:' citation and 3 prose lines
        under it, WHEN the fix runs, THEN the prose is in T-1234's body
        and the file keeps a single-line pointer."""
        _git_init(tmp_path)
        _write_active_ticket(tmp_path, "T-1234")
        _write(
            tmp_path,
            "a.py",
            "# T-1234: narrative\n"
            "# prose line one\n"
            "# prose line two\n"
            "# prose line three\n"
            "def f():\n"
            "    pass\n",
        )
        _add_all(tmp_path)

        queue = load_queue(tmp_path).danger_ok
        applied = fix_docarch002_narrative_move(tmp_path, _snap(tmp_path), queue)

        assert len(applied) == 1
        assert applied[0].rule == "DOCARCH002"
        new_text = (tmp_path / "a.py").read_text()
        assert "prose line one" not in new_text
        assert "# see T-1234 for the history behind this" in new_text
        assert "def f():" in new_text

        moved_queue = load_queue(tmp_path).danger_ok
        body = moved_queue.tickets["T-1234"].body
        assert "prose line one" in body
        assert "prose line two" in body
        assert "prose line three" in body

    # frob:tests src/frob/gates/_fix_engine.py::fix_docarch002_narrative_move
    def test_second_run_is_idempotent(self, tmp_path: Path) -> None:
        """WHEN the fix runs a second time over its own output, THEN
        neither the file nor the ticket body changes (T-2994 constraint
        4)."""
        _git_init(tmp_path)
        _write_active_ticket(tmp_path, "T-1234")
        _write(
            tmp_path,
            "a.py",
            "# T-1234: narrative\n"
            "# prose line one\n"
            "# prose line two\n"
            "def f():\n"
            "    pass\n",
        )
        _add_all(tmp_path)

        queue = load_queue(tmp_path).danger_ok
        first = fix_docarch002_narrative_move(tmp_path, _snap(tmp_path), queue)
        assert len(first) == 1

        text_after_first = (tmp_path / "a.py").read_text()
        body_after_first = load_queue(tmp_path).danger_ok.tickets["T-1234"].body

        queue2 = load_queue(tmp_path).danger_ok
        second = fix_docarch002_narrative_move(tmp_path, _snap(tmp_path), queue2)

        assert second == []
        assert (tmp_path / "a.py").read_text() == text_after_first
        assert load_queue(tmp_path).danger_ok.tickets["T-1234"].body == body_after_first

    # frob:tests src/frob/gates/_fix_engine.py::fix_docarch002_narrative_move
    def test_archived_ticket_writes_archive_path_and_ticket_list_stays_clean(
        self, tmp_path: Path
    ) -> None:
        """GIVEN a fixture citing an ARCHIVED ticket, WHEN the fix runs,
        THEN the body is appended on the ARCHIVED path (T-2994 constraint
        3, the DuplicateId hazard) and `frob ticket list` still exits 0."""
        _git_init(tmp_path)
        _write_archived_ticket(tmp_path, "T-9001")
        _write(
            tmp_path,
            "a.py",
            "# T-9001: narrative\n"
            "# prose line one\n"
            "# prose line two\n"
            "def f():\n"
            "    pass\n",
        )
        _add_all(tmp_path)

        queue = load_queue(tmp_path).danger_ok
        applied = fix_docarch002_narrative_move(tmp_path, _snap(tmp_path), queue)

        assert len(applied) == 1
        # Never wrote a fresh active tickets/T-9001/ -- the DuplicateId
        # hazard T-2678 exists to prevent.
        assert not (tmp_path / "tickets" / "T-9001").is_dir()
        archived_body = (
            tmp_path / "tickets" / "archive" / "T-9001" / "ticket.md"
        ).read_text()
        assert "prose line one" in archived_body

        listed = subprocess.run(
            ["uv", "run", "frob", "ticket", "list"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
        )
        assert listed.returncode == 0

    # frob:tests src/frob/gates/_fix_engine.py::fix_docarch002_narrative_move
    def test_negative_control_directive_citation_is_untouched(
        self, tmp_path: Path
    ) -> None:
        """GIVEN a comment block whose citation is a `frob:ticket`
        directive, WHEN the fix runs, THEN the block is not touched."""
        _git_init(tmp_path)
        _write_active_ticket(tmp_path, "T-1234")
        original = (
            "# frob:ticket T-1234\n"
            "# prose line one\n"
            "# prose line two\n"
            "def f():\n"
            "    pass\n"
        )
        _write(tmp_path, "a.py", original)
        _add_all(tmp_path)

        queue = load_queue(tmp_path).danger_ok
        applied = fix_docarch002_narrative_move(tmp_path, _snap(tmp_path), queue)

        assert applied == []
        assert (tmp_path / "a.py").read_text() == original
        assert load_queue(tmp_path).danger_ok.tickets["T-1234"].body == (
            "## Description\nsomething\n"
        )
