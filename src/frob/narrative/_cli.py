"""`frob narrative move` argparse wiring and runner (T-2993).

Deliberately separate from `src/frob/refactor/_cli.py` (a live, separately
-owned work area this drive) even though both are "author-invoked,
transactional, one-unit-at-a-time" verbs -- this module owns exactly the
narrative-block migration, nothing else.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from frob.logging import get_logger
from frob.narrative._migrate import (
    MigrateError,
    block_at,
    migrate_block,
    moved_text_for_ticket,
)
from frob.render import Renderer

_log = get_logger(__name__)

__all__ = ["add_narrative_parser", "run_narrative_command"]


# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestNarrativeCli.test_add_narrative_parser_registers\
# _move
def add_narrative_parser(sub: argparse._SubParsersAction) -> None:
    """Register `frob narrative move FILE LINE` on an argparse subparsers
    object, matching every other `_add_*_parser` builder's shape
    (`src/frob/_cli_parsers/**`)."""
    p = sub.add_parser("narrative", help="migrate a T-#### narrative comment block")
    narrative_sub = p.add_subparsers(dest="narrative_subcommand", required=True)

    mp = narrative_sub.add_parser(
        "move",
        help="move one # T-####: comment block's narrative into its ticket, "
        "leaving a one-line reference (T-2993; NOT run by land -- author-"
        "invoked only)",
    )
    mp.add_argument("file", type=Path, help="path to the source file")
    mp.add_argument("line", type=int, help="1-indexed line the block starts on")
    mp.add_argument(
        "--keep-file",
        type=Path,
        default=None,
        help="path to a text file containing the exact lines (verbatim, "
        "including leading '#') to keep in place -- omit to move the "
        "whole block, leaving only the one-line reference",
    )
    mp.add_argument(
        "--reason",
        required=True,
        help="frob ticket body's required --reason for the append",
    )
    mp.add_argument(
        "--dry-run",
        action="store_true",
        help="print what would change without writing the file or the ticket",
    )


def _read_keep_lines(keep_file: Path | None) -> tuple[str, ...]:
    """Verbatim lines from `--keep-file`, or `()` when omitted (move the
    whole block)."""
    if keep_file is None:
        return ()
    return tuple(keep_file.read_text(encoding="utf-8").splitlines())


def _already_migrated_in_ticket(ticket_id: str, marker_line: str, root: Path) -> bool:
    """True when `ticket_id`'s REAL current body (not the `""` stand-in
    `migrate_block` validated against) already carries `marker_line` --
    the actual idempotency guard, split out of `run_narrative_command` to
    keep that function under ARCH001's threshold. Degrades to `False` (not
    migrated) on any queue-load failure -- a load error is an unrelated
    problem `set_body` itself will surface, not grounds to refuse a move."""
    from frob.tickets import load_queue

    queue = load_queue(root)
    if queue.is_err or ticket_id not in queue.danger_ok.tickets:
        return False
    return marker_line in queue.danger_ok.tickets[ticket_id].body


def _write_migration(
    *, file_path: Path, migration, ticket_body_text: str, reason: str, root: Path
) -> tuple[int, str]:  # noqa: ANN001
    """The actual write half of `frob narrative move` (file rewrite plus
    `frob.tickets.set_body` append) -- split out of `run_narrative_command`
    to keep that function under ARCH001's threshold. Returns `(exit_code,
    message)`."""
    from frob.tickets import set_body

    file_path.write_text(migration.new_file_text, encoding="utf-8")
    write_result = set_body(
        root, migration.ticket_id, ticket_body_text, mode="append", reason=reason
    )
    if write_result.is_err:
        return 1, (
            f"file updated but ticket body append failed: {write_result.danger_err} "
            f"-- fix the ticket by hand via `frob ticket body {migration.ticket_id}`"
        )
    return 0, (
        f"moved {migration.moved_line_count} line(s) from {file_path} "
        f"into {migration.ticket_id}, kept {migration.kept_line_count} line(s) in place"
    )


# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestNarrativeCli.test_dry_run_reports_without_writing
def run_narrative_command(args: argparse.Namespace) -> int:
    """Execute `frob narrative move` -- resolves the block, computes the
    split, and (unless `--dry-run`) writes the trimmed file plus appends
    the moved text to the named ticket's body via `frob.tickets.set_body`
    (T-2678's proven archived-ticket-safe front door, reused rather than
    reimplemented -- see this ticket's own archived-write-hazard
    constraint)."""
    renderer = Renderer.for_stream(sys.stdout)
    if args.narrative_subcommand != "move":
        renderer.line(f"unknown narrative subcommand: {args.narrative_subcommand}")
        return 2

    file_path: Path = args.file
    try:
        file_text = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        renderer.line(f"could not read {file_path}: {exc}")
        return 1

    extent = block_at(file_text, args.line)
    if extent is None:
        renderer.line(f"{file_path}:{args.line} is not a comment line")
        return 1
    start, end = extent
    keep_lines = _read_keep_lines(args.keep_file)

    result = migrate_block(
        rel_path=str(file_path),
        file_text=file_text,
        start_line=start,
        end_line=end,
        keep_lines=keep_lines,
        existing_ticket_body="",
    )
    if result.is_err:
        err = result.danger_err
        if err is MigrateError.AlreadyMigrated:
            renderer.line(f"{file_path}:{args.line} already migrated -- no-op")
            return 0
        renderer.line(f"narrative move refused: {err}")
        return 1

    migration = result.danger_ok
    lines = file_text.splitlines()
    moved_lines = tuple(ln for ln in lines[start - 1 : end] if ln not in keep_lines)
    ticket_body_text = moved_text_for_ticket(
        rel_path=str(file_path),
        start_line=start,
        moved_lines=moved_lines,
        ticket_id=migration.ticket_id,
    )

    root = Path.cwd()
    marker_line = ticket_body_text.splitlines()[0]
    if _already_migrated_in_ticket(migration.ticket_id, marker_line, root):
        renderer.line(
            f"{file_path}:{args.line} -> {migration.ticket_id} already "
            "migrated -- no-op"
        )
        return 0

    if args.dry_run:
        renderer.line(
            f"DRY RUN: would move {migration.moved_line_count} line(s) from "
            f"{file_path}:{start}-{end} into {migration.ticket_id}, keep "
            f"{migration.kept_line_count} line(s) in place"
        )
        return 0

    exit_code, message = _write_migration(
        file_path=file_path,
        migration=migration,
        ticket_body_text=ticket_body_text,
        reason=args.reason,
        root=root,
    )
    renderer.line(message)
    return exit_code
