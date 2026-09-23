"""`frob.narrative._migrate` unit tests (T-2993): the split logic itself
(keep vs. move), and idempotency -- CLI-level (ticket-store) integration is
proven manually against the live ledger per T-2994's archived-write-hazard
constraint, not re-run here to avoid a live ledger write in unit tests."""

from __future__ import annotations

from frob.narrative._migrate import (
    MigrateError,
    block_at,
    migrate_block,
    moved_text_for_ticket,
    paragraph_at,
    split_ticket_id,
)

_SOCKETD_LIKE_FILE = """\
x = 1

# T-2961: `socketserver.ThreadingUnixStreamServer` is POSIX-only.
# Unlike the fcntl/msvcrt pattern used for FUNCTIONS (T-2918/T-2934/
# T-2952/T-2953), a CLASS statement referencing a missing base at module
# scope raises AttributeError at IMPORT time, not when the daemon is
# used.
if True:
    pass
"""


class TestSplitTicketId:
    """`split_ticket_id` resolves the destination ticket, or refuses."""

    # frob:tests src/frob/narrative/_migrate.py::split_ticket_id
    def test_finds_ticket_id_in_lead_line(self) -> None:
        """A `# T-2961: ...` lead line resolves to `T-2961`."""
        assert split_ticket_id("# T-2961: some text") == "T-2961"

    # frob:tests src/frob/narrative/_migrate.py::split_ticket_id
    def test_no_ticket_id_returns_none(self) -> None:
        """A plain comment with no T-id returns `None`."""
        assert split_ticket_id("# just a comment") is None


class TestBlockAt:
    """`block_at` finds the block's extent from just its first line."""

    # frob:tests src/frob/narrative/_migrate.py::block_at
    def test_finds_multiline_block(self) -> None:
        """The whole contiguous comment run is captured."""
        extent = block_at(_SOCKETD_LIKE_FILE, 3)
        assert extent == (3, 7)

    # frob:tests src/frob/narrative/_migrate.py::block_at
    def test_non_comment_line_returns_none(self) -> None:
        """A line that isn't a comment at all is refused, not guessed at."""
        assert block_at(_SOCKETD_LIKE_FILE, 1) is None


_MD_LIKE_FILE = """\
# Heading

Some intro text.

This paragraph cites T-2678's archived-ticket-safe front door, which is
why the move goes through frob.tickets.set_body.

Next paragraph, unrelated.
"""


class TestParagraphAt:
    """`paragraph_at` (T-2995) is `block_at`'s markdown-prose counterpart:
    a blank-line-delimited span instead of a `#`-comment run."""

    # frob:tests src/frob/narrative/_migrate.py::paragraph_at
    def test_finds_blank_line_delimited_paragraph(self) -> None:
        """The whole paragraph is captured, stopping at the blank line."""
        extent = paragraph_at(_MD_LIKE_FILE, 5)
        assert extent == (5, 6)

    # frob:tests src/frob/narrative/_migrate.py::paragraph_at
    def test_blank_line_returns_none(self) -> None:
        """A blank line itself has no paragraph to find."""
        assert paragraph_at(_MD_LIKE_FILE, 2) is None


class TestMigrateBlockSplit:
    """The keep/move split -- T-2994's own point: this is a caller
    judgement, not something `migrate_block` decides on its own."""

    # frob:tests src/frob/narrative/_migrate.py::migrate_block
    # frob:tests src/frob/narrative/_migrate.py::MigrationResult
    def test_whole_block_moves_when_no_keep_lines_given(self) -> None:
        """With `keep_lines=()`, only the one-line reference remains."""
        result = migrate_block(
            rel_path="src/frob/serve/_socketd.py",
            file_text=_SOCKETD_LIKE_FILE,
            start_line=3,
            end_line=7,
        )
        assert result.is_ok
        migration = result.danger_ok
        assert migration.ticket_id == "T-2961"
        assert migration.kept_line_count == 0
        assert migration.moved_line_count == 5
        new_lines = migration.new_file_text.splitlines()
        assert new_lines[2] == "# see T-2961 for the history behind this"
        # the historical framing is GONE from the file (moved, not kept)
        assert "T-2918" not in migration.new_file_text

    # frob:tests src/frob/narrative/_migrate.py::migrate_block
    def test_load_bearing_sentence_stays_when_named_as_keep(self) -> None:
        """The T-2993 acceptance case: the import-time-crash sentence
        (KEEP) stays in the file; only the cross-reference lines (MOVE)
        leave -- proven on the `_socketd.py` T-2961 block's own shape."""
        lines = _SOCKETD_LIKE_FILE.splitlines()
        keep = (
            lines[2],  # "# T-2961: `socketserver...` is POSIX-only."
            lines[5],  # "# scope raises AttributeError at IMPORT time, ..."
            lines[6],  # "# used."
        )
        result = migrate_block(
            rel_path="src/frob/serve/_socketd.py",
            file_text=_SOCKETD_LIKE_FILE,
            start_line=3,
            end_line=7,
            keep_lines=keep,
        )
        assert result.is_ok
        migration = result.danger_ok
        assert migration.kept_line_count == 3
        assert migration.moved_line_count == 2
        # the import-time-crash explanation survives in the file
        assert "AttributeError at IMPORT time" in migration.new_file_text
        # the historical cross-reference is gone from the file
        assert "T-2918" not in migration.new_file_text
        assert "# see T-2961 for the history behind this" in migration.new_file_text

    # frob:tests src/frob/narrative/_migrate.py::migrate_block
    def test_markdown_paragraph_reference_line_is_plain_prose(self) -> None:
        """T-2995: a `.md` paragraph's reference line is a plain sentence,
        never a `#`-comment (which would render as a heading)."""
        result = migrate_block(
            rel_path="docs/commands/narrative.md",
            file_text=_MD_LIKE_FILE,
            start_line=5,
            end_line=6,
        )
        assert result.is_ok
        migration = result.danger_ok
        assert migration.ticket_id == "T-2678"
        assert "See T-2678 for the history behind this." in migration.new_file_text
        assert "# see" not in migration.new_file_text

    # frob:tests src/frob/narrative/_migrate.py::MigrateError
    # frob:tests src/frob/narrative/_migrate.py::migrate_block
    def test_no_ticket_id_refuses(self) -> None:
        """A block that names no ticket cannot be routed anywhere."""
        text = "# just a comment\n# more comment\n"
        result = migrate_block(
            rel_path="f.py", file_text=text, start_line=1, end_line=2
        )
        assert result.is_err
        assert result.danger_err is MigrateError.NoTicketId

    # frob:tests src/frob/narrative/_migrate.py::migrate_block
    def test_keep_line_not_in_block_refuses(self) -> None:
        """A `keep_lines` entry that is not verbatim IN the block is
        refused rather than silently ignored -- ambiguity is a hard
        error, not a guess."""
        result = migrate_block(
            rel_path="src/frob/serve/_socketd.py",
            file_text=_SOCKETD_LIKE_FILE,
            start_line=3,
            end_line=7,
            keep_lines=("# this line does not exist in the block",),
        )
        assert result.is_err
        assert result.danger_err is MigrateError.AmbiguousKeepLines

    # frob:tests src/frob/narrative/_migrate.py::migrate_block
    def test_bad_line_range_refuses(self) -> None:
        """An out-of-range line pair is `BlockNotFound`, not an IndexError."""
        result = migrate_block(
            rel_path="f.py", file_text="x = 1\n", start_line=5, end_line=9
        )
        assert result.is_err
        assert result.danger_err is MigrateError.BlockNotFound


class TestIdempotency:
    """T-2994 constraint 4: running the migration twice must not
    duplicate content into the ticket."""

    # frob:tests src/frob/narrative/_migrate.py::moved_text_for_ticket
    # frob:tests src/frob/narrative/_migrate.py::migrate_block
    def test_marker_already_present_refuses_as_already_migrated(self) -> None:
        """A second call against the same file/line/ticket, with the
        ticket's real body already carrying the marker, refuses cleanly
        instead of appending a second copy."""
        first = migrate_block(
            rel_path="src/frob/serve/_socketd.py",
            file_text=_SOCKETD_LIKE_FILE,
            start_line=3,
            end_line=7,
        )
        assert first.is_ok
        moved_lines = tuple(_SOCKETD_LIKE_FILE.splitlines()[2:7])
        ticket_text = moved_text_for_ticket(
            rel_path="src/frob/serve/_socketd.py",
            start_line=3,
            moved_lines=moved_lines,
            ticket_id="T-2961",
        )
        marker_line = ticket_text.splitlines()[0]
        simulated_ticket_body = f"some existing prose\n\n{ticket_text}\n"
        second = migrate_block(
            rel_path="src/frob/serve/_socketd.py",
            file_text=_SOCKETD_LIKE_FILE,
            start_line=3,
            end_line=7,
            existing_ticket_body=simulated_ticket_body,
        )
        assert second.is_err
        assert second.danger_err is MigrateError.AlreadyMigrated
        assert marker_line in simulated_ticket_body


class TestNarrativeCli:
    """`frob narrative move` argparse wiring and a `--dry-run` smoke test
    (TEST001 coverage for `add_narrative_parser`/`run_narrative_command`)."""

    # frob:tests src/frob/narrative/_cli.py::add_narrative_parser
    def test_add_narrative_parser_registers_move(self) -> None:
        """`frob narrative move FILE LINE` parses into the expected
        Namespace shape."""
        import argparse

        from frob.narrative._cli import add_narrative_parser

        parser = argparse.ArgumentParser(prog="frob")
        sub = parser.add_subparsers(dest="subcommand")
        add_narrative_parser(sub)
        args = parser.parse_args(["narrative", "move", "f.py", "3", "--reason", "why"])
        assert args.narrative_subcommand == "move"
        assert args.line == 3
        assert args.reason == "why"

    # frob:tests src/frob/narrative/_cli.py::run_narrative_command
    def test_dry_run_reports_without_writing(self, tmp_path) -> None:
        """`--dry-run` against a fixture file with a real T-id block
        reports the intended move and leaves the file untouched."""
        import argparse

        from frob.narrative._cli import add_narrative_parser, run_narrative_command

        target = tmp_path / "demo.py"
        target.write_text(_SOCKETD_LIKE_FILE, encoding="utf-8")
        before = target.read_text(encoding="utf-8")

        parser = argparse.ArgumentParser(prog="frob")
        sub = parser.add_subparsers(dest="subcommand")
        add_narrative_parser(sub)
        args = parser.parse_args(
            ["narrative", "move", str(target), "3", "--reason", "why", "--dry-run"]
        )
        exit_code = run_narrative_command(args)
        assert exit_code == 0
        assert target.read_text(encoding="utf-8") == before


class TestNarrativeIntegration:
    """Real subprocess `python -m frob narrative move` invocation (TEST003:
    every interface needs >=1 integration test) -- exercises the actual
    `frob` dispatch (`__main__._dispatch_narrative`), not just the library
    functions the rest of this file calls directly."""

    def test_frob_narrative_move_dry_run_via_subprocess(self, tmp_path) -> None:
        # frob:tests src/frob/narrative kind="integration"
        import subprocess
        import sys

        target = tmp_path / "demo.py"
        target.write_text(_SOCKETD_LIKE_FILE, encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "frob",
                "narrative",
                "move",
                str(target),
                "3",
                "--reason",
                "integration test",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert "T-2961" in result.stdout
        # dry-run must never touch the file
        assert target.read_text(encoding="utf-8") == _SOCKETD_LIKE_FILE


class TestDirectiveLinesPreserved:
    """T-5108: `frob narrative move`'s default (no `--keep-file`) mode
    must never delete a directive line (`frob:doc`/`frob:waive`/`frob:
    invariant`/...) that sits inside the moved comment run -- only the
    prose leaves. Positive control is the ticket's own body: a run with
    prose plus one `frob:doc`, one `frob:waive`, and one multi-line
    `frob:invariant` block."""

    # T-5108: built line-by-line (never a bare triple-quoted block) so no
    # RAW SOURCE line in this file itself starts with '#' -- a prior
    # version wrote this fixture as a plain '"""...""" ' block, and the
    # land's own pre-land FMT001 directive-wrap pass (which scans PHYSICAL
    # file lines for a '# frob:...' continuation shape, blind to whether
    # that line sits inside a Python string literal) reflowed and
    # corrupted the embedded backslash-continuation payload before it
    # ever reached this test. Each element below is its own string
    # literal on its own source line, indented past column 0, so no
    # physical line in THIS file matches that scanner's directive-lead
    # shape.
    _FIXTURE_LINES = (
        "x = 1",
        "",
        "# T-3001: this daemon's shutdown path was rewritten twice before landing",
        "# on the current design -- the first attempt raced a signal handler",
        "# against a background thread join and hung under load.",
        "# frob:doc docs/modules/daemon.md#shutdown",
        '# frob:waive PII012 reason="fixture-only, no real PII in this test path"',
        "# frob:invariant INV-042 \\",
        "# the shutdown path must never join the background thread from inside \\",
        "# the signal handler itself",
        "if True:",
        "    pass",
        "",
    )
    _FIXTURE = "\n".join(_FIXTURE_LINES)

    def _directive_lines(self) -> tuple[str, ...]:
        return (
            "# frob:doc docs/modules/daemon.md#shutdown",
            '# frob:waive PII012 reason="fixture-only, no real PII in this test path"',
            "# frob:invariant INV-042 \\",
            "# the shutdown path must never join the background thread from inside \\",
            "# the signal handler itself",
        )

    # frob:tests src/frob/narrative/_cli.py::_directive_keep_lines
    def test_directive_keep_lines_finds_lead_and_continuation_lines(self) -> None:
        """`_directive_keep_lines` returns every directive lead line plus
        its backslash-continuation payload lines, in block order, and
        nothing else (no prose)."""
        from frob.narrative._cli import _directive_keep_lines

        block = self._FIXTURE.splitlines()[2:11]
        assert _directive_keep_lines(block) == self._directive_lines()

    def _write_active_ticket(self, root, ticket_id: str) -> None:
        """A minimal v2 active ticket, matching `test_bulk.py`'s own
        `_write_active_ticket` shape."""
        from datetime import date

        from frob.tickets._models import Origin, Ticket, TicketKind, TicketState
        from frob.tickets._store import _serialize_ticket

        d = root / "tickets" / ticket_id
        d.mkdir(parents=True)
        ticket = Ticket(
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
        (d / "ticket.md").write_text(_serialize_ticket(ticket))

    # frob:tests src/frob/narrative/_cli.py::run_narrative_command
    def test_positive_control_keeps_directives_moves_only_prose(
        self, tmp_path, monkeypatch
    ) -> None:
        """GIVEN a run containing prose plus one `frob:doc`, one `frob:
        waive`, and one multi-line `frob:invariant`, WHEN `frob narrative
        move` runs (no `--keep-file`), THEN the file keeps all three
        directives byte-for-byte and none of the prose, and the ticket
        body receives only the prose."""
        import argparse

        from frob.narrative._cli import add_narrative_parser, run_narrative_command

        monkeypatch.chdir(tmp_path)
        self._write_active_ticket(tmp_path, "T-3001")
        target = tmp_path / "demo.py"
        target.write_text(self._FIXTURE, encoding="utf-8")

        parser = argparse.ArgumentParser(prog="frob")
        sub = parser.add_subparsers(dest="subcommand")
        add_narrative_parser(sub)
        args = parser.parse_args(
            [
                "narrative",
                "move",
                str(target),
                "3",
                "--reason",
                "T-5108 positive control",
            ]
        )
        exit_code = run_narrative_command(args)
        assert exit_code == 0

        new_text = target.read_text(encoding="utf-8")
        for directive_line in self._directive_lines():
            assert directive_line in new_text.splitlines()
        assert "shutdown path was rewritten twice" not in new_text
        assert "raced a signal handler" not in new_text

        from frob.tickets import load_queue

        body = load_queue(tmp_path).danger_ok.tickets["T-3001"].body
        assert "shutdown path was rewritten twice" in body
        assert "frob:doc docs/modules/daemon.md#shutdown" not in body
        assert "frob:invariant INV-042" not in body

    # frob:tests src/frob/narrative/_cli.py::run_narrative_command
    def test_diff_of_moved_file_removes_no_directive_line(
        self, tmp_path, monkeypatch
    ) -> None:
        """Regression coverage for the agent's own detection recipe: the
        diff of a moved file must contain no REMOVED directive line."""
        import argparse
        import difflib

        from frob.narrative._cli import add_narrative_parser, run_narrative_command

        monkeypatch.chdir(tmp_path)
        self._write_active_ticket(tmp_path, "T-3001")
        target = tmp_path / "demo.py"
        before = self._FIXTURE
        target.write_text(before, encoding="utf-8")

        parser = argparse.ArgumentParser(prog="frob")
        sub = parser.add_subparsers(dest="subcommand")
        add_narrative_parser(sub)
        args = parser.parse_args(
            ["narrative", "move", str(target), "3", "--reason", "T-5108 regression"]
        )
        exit_code = run_narrative_command(args)
        assert exit_code == 0

        after = target.read_text(encoding="utf-8")
        diff = difflib.unified_diff(
            before.splitlines(), after.splitlines(), lineterm=""
        )
        removed_directive_lines = [
            line
            for line in diff
            if line.startswith("-")
            and not line.startswith("---")
            and line[1:] in self._directive_lines()
        ]
        assert removed_directive_lines == []
