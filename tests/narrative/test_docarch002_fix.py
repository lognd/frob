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


class TestDocarch002PreLandPlanOnly:
    """T-5347: the pre-land Tier-A pass (`merge_target_ids` given, T-2400's
    own land signal) must load the ticket archive at most ONCE per run and
    must never write a ticket body -- the measured incident (a repo-wide
    pre-land pass reparsing the whole archive YAML per finding, plus
    writing ledger bodies as a side effect of landing an unrelated
    ticket) that wedged lands for 18-52 minutes."""

    def _fixture_repo(self, tmp_path: Path) -> None:
        """10 files, 5 DOCARCH002 citation-shape findings each (50
        total), every citation pointing at an ARCHIVED ticket -- forces
        `_docarch002_existing_body` to actually consult the archive
        cache for every single finding, so a per-finding reload (the
        T-5347 bug) would have shown up as 50 `load_archive` calls. Each
        finding's comment run is separated from its neighbor by a blank
        line -- `scan_citation_shape` treats a contiguous comment run as
        ONE finding, so without a break, 5 back-to-back citation blocks
        in the same file would scan as a single (bigger) finding rather
        than 5 distinct ones."""
        _git_init(tmp_path)
        for file_idx in range(10):
            ticket_id = f"T-91{file_idx:02d}"
            _write_archived_ticket(tmp_path, ticket_id)
            lines: list[str] = []
            for finding_idx in range(5):
                if finding_idx:
                    lines.append("")
                lines.append(f"# {ticket_id}: narrative block {finding_idx}")
                lines.append(f"# prose line a {finding_idx}")
                lines.append(f"# prose line b {finding_idx}")
            lines.append("")
            lines.append("def f():")
            lines.append("    pass")
            _write(tmp_path, f"file_{file_idx}.py", "\n".join(lines) + "\n")
        _add_all(tmp_path)

    # frob:tests \
    # tests/narrative/test_docarch002_fix.py::TestDocarch002PreLandPlanOnly.test_archive_loaded_once_and_zero_ledger_writes_in_pre_land_mode  # noqa: E501
    def test_archive_loaded_once_and_zero_ledger_writes_in_pre_land_mode(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """GIVEN a fixture with 50 DOCARCH002 findings across 10 files
        all citing archived tickets, WHEN `apply_tier_a_fixes` runs with
        `merge_target_ids` given (pre-land mode), THEN the archive is
        loaded exactly once and zero ticket bodies/files are written."""
        import frob.tickets._store as _store_mod
        from frob.gates._fix_engine import MergeTargetKnownIds, apply_tier_a_fixes
        from frob.graph import build_graph

        self._fixture_repo(tmp_path)

        call_count = {"n": 0}
        real_load_archive = _store_mod.load_archive

        def counting_load_archive(root):  # noqa: ANN001, ANN202
            call_count["n"] += 1
            return real_load_archive(root)

        monkeypatch.setattr(_store_mod, "load_archive", counting_load_archive)

        snapshot = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
        queue = load_queue(tmp_path).danger_ok
        before_bodies = {
            f"T-91{i:02d}": (
                tmp_path / "tickets" / "archive" / f"T-91{i:02d}" / "ticket.md"
            ).read_text()
            for i in range(10)
        }
        before_files = {
            f"file_{i}.py": (tmp_path / f"file_{i}.py").read_text() for i in range(10)
        }

        from frob.gates._fix_engine import TIER_A_HANDLERS

        other_rules = tuple(r for r in TIER_A_HANDLERS if r != "DOCARCH002")
        applied = apply_tier_a_fixes(
            tmp_path,
            snapshot,
            queue,
            exclude=other_rules,
            ticket_id="T-9999",
            merge_target_ids=MergeTargetKnownIds(),
        )

        assert call_count["n"] == 1
        assert [fix for fix in applied if fix.rule == "DOCARCH002"] == []
        for i in range(10):
            ticket_id = f"T-91{i:02d}"
            after_body = (
                tmp_path / "tickets" / "archive" / ticket_id / "ticket.md"
            ).read_text()
            assert after_body == before_bodies[ticket_id]
            assert (tmp_path / f"file_{i}.py").read_text() == before_files[
                f"file_{i}.py"
            ]

    # frob:tests \
    # tests/narrative/test_docarch002_fix.py::TestDocarch002PreLandPlanOnly.test_bare_check_fix_mode_still_writes  # noqa: E501
    def test_bare_check_fix_mode_still_writes(self, tmp_path: Path) -> None:
        """GIVEN the same 50-finding fixture, WHEN `fix_docarch002_
        narrative_move` runs with NO `merge_target_ids` (a bare `frob
        check --fix`), THEN it still performs real moves -- T-5347's
        plan-only gating is land-pre-land-specific, not a regression on
        T-4694's original behavior."""
        from frob.gates._fix_engine import fix_docarch002_narrative_move

        self._fixture_repo(tmp_path)
        queue = load_queue(tmp_path).danger_ok

        applied = fix_docarch002_narrative_move(tmp_path, _snap(tmp_path), queue)

        assert len(applied) == 50
        new_text = (tmp_path / "file_0.py").read_text()
        assert "prose line a 0" not in new_text
        assert "# see T-9100 for the history behind this" in new_text
