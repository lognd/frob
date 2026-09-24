"""`frob narrative move`'s bulk mode (T-4697): the positive control from
this ticket's own body -- a fixture directory of three files citing a
live ticket, an archived ticket, and no ticket -- plus the idempotency
and dry-run acceptance criteria.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from frob.narrative._bulk import (
    apply_bulk,
    discover_targets,
    find_blocks,
    plan_bulk,
)
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
from frob.tickets._store import _serialize_ticket


# frob:ticket T-4697
def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


# frob:ticket T-4697
def _make_ticket(ticket_id: str, title: str = "Sample") -> Ticket:
    """A minimal queued `Ticket`, matching `test_ticket_store.py`'s own
    `_ticket` helper shape."""
    return Ticket(
        id=ticket_id,
        title=title,
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


# frob:ticket T-4697
def _write_active_ticket(root: Path, ticket_id: str) -> None:
    """Create `tickets/<id>/ticket.md` (v2, active) directly on disk."""
    d = root / "tickets" / ticket_id
    d.mkdir(parents=True)
    (d / "ticket.md").write_text(_serialize_ticket(_make_ticket(ticket_id)))


# frob:ticket T-4697
def _write_archived_ticket(root: Path, ticket_id: str) -> None:
    """Create `tickets/archive/<id>/ticket.md` (v2, archived) directly on
    disk -- `set_body` must amend this path in place (T-2678)."""
    d = root / "tickets" / "archive" / ticket_id
    d.mkdir(parents=True)
    (d / "ticket.md").write_text(_serialize_ticket(_make_ticket(ticket_id)))


# frob:ticket T-4697
class TestFindBlocks:
    """`find_blocks` -- discovery over both source and markdown shapes."""

    # frob:ticket T-4697
    # frob:tests src/frob/narrative/_bulk.py::find_blocks
    def test_finds_python_ticket_lead_block(self) -> None:
        """A `# T-####:`-lead comment run of 13+ lines (NARR001's own
        shape) is discovered in a `.py` file."""
        text = "\n".join(["# T-1234: narrative"] + [f"# line {i}" for i in range(13)])
        blocks = find_blocks(Path("a.py"), text)
        assert blocks == ((1, 14),)

    # frob:ticket T-4697
    # frob:tests src/frob/narrative/_bulk.py::find_blocks
    def test_finds_markdown_paragraph(self) -> None:
        """A blank-line-delimited paragraph citing a ticket id is
        discovered in a `.md` file."""
        text = "intro\n\nSee T-9999 for background on this decision.\n\nmore\n"
        blocks = find_blocks(Path("a.md"), text)
        assert blocks == ((3, 3),)

    # frob:ticket T-4697
    def test_reference_line_is_not_rediscovered(self) -> None:
        """The one-line replacement `migrate_block` itself writes is
        excluded from re-detection -- the idempotency guard bulk mode
        needs beyond the source block simply vanishing."""
        text = "intro\n\nSee T-9999 for the history behind this.\n\nmore\n"
        blocks = find_blocks(Path("a.md"), text)
        assert blocks == ()


# frob:ticket T-4697
class TestDiscoverTargets:
    """`discover_targets` -- file vs. directory dispatch."""

    # frob:ticket T-4697
    # frob:tests src/frob/narrative/_bulk.py::discover_targets
    def test_file_returns_itself(self, tmp_path: Path) -> None:
        """A file target returns exactly itself."""
        f = _write(tmp_path, "a.py", "# x\n")
        assert discover_targets(f) == (f,)

    # frob:ticket T-4697
    # frob:tests src/frob/narrative/_bulk.py::discover_targets
    def test_directory_returns_scanned_suffixes_recursively(
        self, tmp_path: Path
    ) -> None:
        """A directory target returns every `.py`/`.strata`/`.md` file
        under it, recursively, and nothing else."""
        _write(tmp_path, "a.py", "# x\n")
        _write(tmp_path, "sub/b.md", "x\n")
        _write(tmp_path, "c.txt", "x\n")
        found = discover_targets(tmp_path)
        assert {p.name for p in found} == {"a.py", "b.md"}


# frob:ticket T-4697
class TestPlanBulk:
    """`plan_bulk` -- the dry-run listing (no writes)."""

    # frob:ticket T-4697
    # frob:tests src/frob/narrative/_bulk.py::BulkItem
    # frob:tests src/frob/narrative/_bulk.py::plan_bulk
    # frob:tests src/frob/narrative/_bulk.py::BulkPlan
    def test_plan_lists_every_block_with_its_ticket(self, tmp_path: Path) -> None:
        """The plan enumerates each block found, its resolved ticket id
        (or `None`), and writes nothing."""
        _write(
            tmp_path,
            "a.py",
            "\n".join(["# T-1234: narrative"] + [f"# line {i}" for i in range(13)])
            + "\n",
        )
        plan = plan_bulk(tmp_path)
        assert len(plan.items) == 1
        assert plan.items[0].ticket_id == "T-1234"
        assert plan.items[0].status == "planned"
        # No file mutation from planning alone.
        assert "T-1234: narrative" in (tmp_path / "a.py").read_text()


# frob:ticket T-4697
class TestApplyBulk:
    """`apply_bulk` -- the real sweep: move, skip, and idempotency."""

    # frob:ticket T-4697
    def _fixture_dir(self, tmp_path: Path) -> Path:
        """The ticket's own positive control: three files, one citing a
        live ticket, one an archived ticket, one no ticket at all."""
        _write_active_ticket(tmp_path, "T-1001")
        _write_archived_ticket(tmp_path, "T-1002")

        sweep_dir = tmp_path / "sweep"
        _write(
            sweep_dir,
            "live.py",
            "\n".join(["# T-1001: live narrative"] + [f"# line {i}" for i in range(13)])
            + "\ndef f():\n    pass\n",
        )
        _write(
            sweep_dir,
            "archived.py",
            "\n".join(
                ["# T-1002: archived narrative"] + [f"# line {i}" for i in range(13)]
            )
            + "\ndef g():\n    pass\n",
        )
        _write(
            sweep_dir,
            "untargeted.py",
            "\n".join(
                ["# T-9999: cites no real ticket"] + [f"# line {i}" for i in range(13)]
            )
            + "\ndef h():\n    pass\n",
        )
        return sweep_dir

    # frob:ticket T-4697
    # frob:tests src/frob/narrative/_bulk.py::apply_bulk
    def test_apply_false_writes_nothing(self, tmp_path: Path) -> None:
        """Omitting `--apply` (apply=False) returns the plan and writes
        neither source files nor any ticket body."""
        sweep_dir = self._fixture_dir(tmp_path)
        before = (sweep_dir / "live.py").read_text()
        plan = apply_bulk(sweep_dir, apply=False, reason="test", root=tmp_path)
        assert len(plan.items) == 3
        assert (sweep_dir / "live.py").read_text() == before
        archived_body = (
            tmp_path / "tickets" / "archive" / "T-1002" / "ticket.md"
        ).read_text()
        assert "archived narrative" not in archived_body

    # frob:tests src/frob/narrative/_bulk.py::apply_bulk

    # frob:ticket T-4697
    def test_apply_moves_live_and_archived_skips_untargeted(
        self, tmp_path: Path
    ) -> None:
        """`--apply` moves the live- and archived-ticket blocks into
        their ticket bodies with a one-line pointer left behind, and
        SKIPS (never deletes) the block citing a ticket that does not
        exist."""
        sweep_dir = self._fixture_dir(tmp_path)
        plan = apply_bulk(sweep_dir, apply=True, reason="test sweep", root=tmp_path)

        # T-5478: rel_path is str(Path) -- native separator (backslash on
        # Windows). Path(...).name is separator-agnostic; a hardcoded
        # '/' split silently no-ops on Windows and every key stays the
        # full path instead of the basename.
        statuses = {Path(i.rel_path).name: i.status for i in plan.items}
        assert statuses["live.py"] == "moved"
        assert statuses["archived.py"] == "moved"
        assert statuses["untargeted.py"] == "skipped"

        live_text = (sweep_dir / "live.py").read_text()
        assert "live narrative" not in live_text
        assert "see T-1001" in live_text

        untargeted_text = (sweep_dir / "untargeted.py").read_text()
        assert "T-9999: cites no real ticket" in untargeted_text

        active_body = (tmp_path / "tickets" / "T-1001" / "ticket.md").read_text()
        assert "live narrative" in active_body

        archived_body = (
            tmp_path / "tickets" / "archive" / "T-1002" / "ticket.md"
        ).read_text()
        assert "archived narrative" in archived_body

        from frob.tickets import load_all

        assert load_all(tmp_path).is_ok

    # frob:ticket T-4697
    # frob:tests src/frob/narrative/_bulk.py::apply_bulk
    def test_second_apply_is_idempotent_noop(self, tmp_path: Path) -> None:
        """Running `--apply` a second time changes nothing in any file or
        ticket body (T-2994 constraint 4)."""
        sweep_dir = self._fixture_dir(tmp_path)
        apply_bulk(sweep_dir, apply=True, reason="first sweep", root=tmp_path)

        live_after_first = (sweep_dir / "live.py").read_text()
        active_body_after_first = (
            tmp_path / "tickets" / "T-1001" / "ticket.md"
        ).read_text()

        plan2 = apply_bulk(sweep_dir, apply=True, reason="second sweep", root=tmp_path)

        assert (sweep_dir / "live.py").read_text() == live_after_first
        assert (
            tmp_path / "tickets" / "T-1001" / "ticket.md"
        ).read_text() == active_body_after_first
        # The reference line itself is no longer a discoverable block, so
        # the second sweep finds nothing left to move for live.py/archived.py.
        moved_files = {
            Path(i.rel_path).name for i in plan2.items if i.status == "moved"
        }
        assert "live.py" not in moved_files
        assert "archived.py" not in moved_files
