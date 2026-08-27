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

    def test_finds_ticket_id_in_lead_line(self) -> None:
        """A `# T-2961: ...` lead line resolves to `T-2961`."""
        assert split_ticket_id("# T-2961: some text") == "T-2961"

    def test_no_ticket_id_returns_none(self) -> None:
        """A plain comment with no T-id returns `None`."""
        assert split_ticket_id("# just a comment") is None


class TestBlockAt:
    """`block_at` finds the block's extent from just its first line."""

    def test_finds_multiline_block(self) -> None:
        """The whole contiguous comment run is captured."""
        extent = block_at(_SOCKETD_LIKE_FILE, 3)
        assert extent == (3, 7)

    def test_non_comment_line_returns_none(self) -> None:
        """A line that isn't a comment at all is refused, not guessed at."""
        assert block_at(_SOCKETD_LIKE_FILE, 1) is None


class TestMigrateBlockSplit:
    """The keep/move split -- T-2994's own point: this is a caller
    judgement, not something `migrate_block` decides on its own."""

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

    def test_no_ticket_id_refuses(self) -> None:
        """A block that names no ticket cannot be routed anywhere."""
        text = "# just a comment\n# more comment\n"
        result = migrate_block(
            rel_path="f.py", file_text=text, start_line=1, end_line=2
        )
        assert result.is_err
        assert result.danger_err is MigrateError.NoTicketId

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
