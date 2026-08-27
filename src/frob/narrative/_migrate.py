"""`frob narrative move` -- author-invoked migration of one `# T-####:`
narrative comment block into the ticket it already names (T-2993).

NOT wired into `land` (T-2994's own doctrine: land may CHECK, never
REWRITE -- see this module's own package docstring). This is a deliberate,
reviewable, single-block edit an author or agent runs by hand, exactly
the shape `frob refactor move`/`rename` already established for source
rewrites in this repo (`src/frob/refactor/_cli.py`) -- this module does
not reuse that CLI surface directly (it is a live, separately-owned work
area this drive) but matches its "author-invoked, one unit at a time,
transactional" posture.

THE SPLIT ITSELF IS NOT AUTOMATED HERE. T-2993/T-2994 are explicit that
which lines are archaeology (MOVE) versus load-bearing utility (KEEP) is
a judgement call, not a regex -- the `_socketd.py`/T-2961 example mixes
both in one block. `migrate_block` therefore takes the caller's own
`keep_lines` (already decided) and moves everything else in the block,
rather than guessing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from typani.error_set import ErrorSet
from typani.result import Err, Ok, Result

from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "MigrateError",
    "MigrationResult",
    "block_at",
    "migrate_block",
    "moved_text_for_ticket",
    "paragraph_at",
    "split_ticket_id",
]

_TICKET_ID_RE = re.compile(r"T-\d{2,6}")
_MARKER_TEMPLATE = "<!-- narrative-moved:{file}:{line}:{ticket} -->"


# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_no_ticket_id_refuses
class MigrateError(ErrorSet):
    """Failure modes for `migrate_block` -- one recoverable value per
    reason a move cannot proceed, never a bare exception, matching this
    repo's typani `Result`-everywhere convention."""

    BlockNotFound = "no comment block starts at the given file/line"
    NoTicketId = "the block names no T-#### id to move the text into"
    AmbiguousKeepLines = "keep_lines is not a subset of the block's own lines"
    AlreadyMigrated = "this exact block was already moved (idempotent no-op)"


# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_whole_block_moves_when_no\
# _keep_lines_given
@dataclass(frozen=True)
class MigrationResult:
    """What `migrate_block` did: the ticket the text moved to, how many
    lines moved versus stayed, and the replacement text now in the file
    (so the caller writes it back and can show a diff before committing)."""

    ticket_id: str
    moved_line_count: int
    kept_line_count: int
    new_file_text: str
    already_migrated: bool


# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestSplitTicketId.test_finds_ticket_id_in_lead_line
# frob:tests \
# tests/test_narrative_migrate.py::TestSplitTicketId.test_no_ticket_id_returns_none
def split_ticket_id(lead_line: str) -> str | None:
    """The `T-####` id in a block's lead line (`# T-2961: ...`), or `None`
    if the line names no ticket -- `migrate_block` refuses with
    `MigrateError.NoTicketId` when this comes back `None` rather than
    guessing a destination."""
    m = _TICKET_ID_RE.search(lead_line)
    return m.group(0) if m else None


def _marker(rel_path: str, line: int, ticket_id: str) -> str:
    """The idempotency marker embedded in the ticket body text so a second
    `migrate_block` call over the SAME file/line/ticket triple detects the
    prior move and refuses rather than appending the narrative twice
    (T-2994 constraint 4: idempotency)."""
    return _MARKER_TEMPLATE.format(file=rel_path, line=line, ticket=ticket_id)


def _validate_block(
    *,
    rel_path: str,
    lines: list[str],
    start_line: int,
    end_line: int,
    keep_lines: tuple[str, ...],
    existing_ticket_body: str,
) -> Result[tuple[list[str], str], MigrateError]:
    """`migrate_block`'s pre-rewrite validation, split out to keep that
    function under ARCH001's length threshold: resolves the block's own
    lines and destination ticket id, or refuses with the specific
    `MigrateError` -- `BlockNotFound`/`NoTicketId`/`AmbiguousKeepLines`/
    `AlreadyMigrated` -- covering why. Returns `(block, ticket_id)` on
    success."""
    n = len(lines)
    if not (1 <= start_line <= n and start_line <= end_line <= n):
        return Err(MigrateError.BlockNotFound)
    block = lines[start_line - 1 : end_line]
    if not block or not block[0].strip():
        return Err(MigrateError.BlockNotFound)

    # T-2995: a `# T-####:` code comment always names its ticket on the
    # lead line (split_ticket_id's single-line search), but a markdown
    # paragraph migrated via `paragraph_at` may cite it anywhere in the
    # prose -- fall back to a whole-block search so the doc case works
    # through the same validation path rather than a second one.
    ticket_id = split_ticket_id(block[0]) or split_ticket_id("\n".join(block))
    if ticket_id is None:
        return Err(MigrateError.NoTicketId)

    if any(kl not in block for kl in keep_lines):
        return Err(MigrateError.AmbiguousKeepLines)

    marker = _marker(rel_path, start_line, ticket_id)
    if marker in existing_ticket_body:
        _log.debug(
            "narrative_migrate: %s:%d -> %s already migrated (marker present)",
            rel_path,
            start_line,
            ticket_id,
        )
        return Err(MigrateError.AlreadyMigrated)

    return Ok((block, ticket_id))


# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_whole_block_moves_when_no\
# _keep_lines_given
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_load_bearing_sentence_sta\
# ys_when_named_as_keep
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_no_ticket_id_refuses
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_keep_line_not_in_block_re\
# fuses
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_bad_line_range_refuses
# frob:tests \
# tests/test_narrative_migrate.py::TestIdempotency.test_marker_already_present_refuses_\
# as_already_migrated
# frob:tests \
# tests/test_narrative_migrate.py::TestMigrateBlockSplit.test_markdown_paragraph_refere\
# nce_line_is_plain_prose
def migrate_block(
    *,
    rel_path: str,
    file_text: str,
    start_line: int,
    end_line: int,
    keep_lines: tuple[str, ...] = (),
    existing_ticket_body: str = "",
) -> Result[MigrationResult, MigrateError]:
    """Move the comment block at 1-indexed `file_text` lines
    `[start_line, end_line]` (inclusive) into its named ticket, leaving
    `keep_lines` (verbatim, caller-selected KEEP text -- may be empty) plus
    a one-line `# see T-####: <old first words>` reference in the file.

    Pure function: takes the CURRENT file text and the ticket's CURRENT
    body text, returns the NEW file text and the text to append to the
    ticket body (via the marker embedded in `MigrationResult`'s caller
    contract below) -- no filesystem or ticket-store I/O happens here, so
    this is fixture-testable without a live ledger, and the CLI layer
    (`_cli.py`) does the actual `set_body`/file-write once this returns
    `Ok`. `existing_ticket_body` lets the caller pass the ticket's real
    current body so idempotency (constraint 4) is checked before any
    write happens.
    """
    lines = file_text.splitlines()
    validated = _validate_block(
        rel_path=rel_path,
        lines=lines,
        start_line=start_line,
        end_line=end_line,
        keep_lines=keep_lines,
        existing_ticket_body=existing_ticket_body,
    )
    if validated.is_err:
        return Err(validated.danger_err)
    block, ticket_id = validated.danger_ok

    moved = [ln for ln in block if ln not in keep_lines]
    # T-2995: a markdown paragraph's reference line is plain prose (a "#"
    # prefix would render as a heading), never the "#"-comment shape a
    # code block's reference line uses.
    if rel_path.endswith(".md"):
        reference_line = f"See {ticket_id} for the history behind this."
    else:
        kept_indent = "#"
        for ln in block:
            stripped = ln.lstrip()
            if stripped.startswith("#"):
                kept_indent = ln[: len(ln) - len(stripped)] + "#"
                break
        reference_line = f"{kept_indent} see {ticket_id} for the history behind this"
    replacement = list(keep_lines) + [reference_line]

    new_lines = lines[: start_line - 1] + replacement + lines[end_line:]
    new_file_text = "\n".join(new_lines)
    if file_text.endswith("\n"):
        new_file_text += "\n"

    return Ok(
        MigrationResult(
            ticket_id=ticket_id,
            moved_line_count=len(moved),
            kept_line_count=len(keep_lines),
            new_file_text=new_file_text,
            already_migrated=False,
        )
    )


# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestIdempotency.test_marker_already_present_refuses_\
# as_already_migrated
def moved_text_for_ticket(
    *, rel_path: str, start_line: int, moved_lines: tuple[str, ...], ticket_id: str
) -> str:
    """The exact text `migrate_block`'s CLI caller appends to the ticket's
    body via `frob.tickets.set_body(..., mode='append')`: the idempotency
    marker (T-2994 constraint 4) followed by the moved lines verbatim,
    with their leading `#`/whitespace stripped -- ticket bodies are plain
    markdown prose, not source comments."""
    marker = _marker(rel_path, start_line, ticket_id)
    stripped = [re.sub(r"^\s*#\s?", "", ln) for ln in moved_lines]
    body = "\n".join(stripped).strip()
    return f"{marker}\n{body}" if body else marker


# frob:doc docs/commands/narrative.md#usage
# frob:tests tests/test_narrative_migrate.py::TestBlockAt.test_finds_multiline_block
# frob:tests \
# tests/test_narrative_migrate.py::TestBlockAt.test_non_comment_line_returns_none
def block_at(file_text: str, start_line: int) -> tuple[int, int] | None:
    """The `(start, end)` 1-indexed inclusive range of the contiguous
    `#`-comment block beginning at `start_line`, or `None` if `start_line`
    is not itself a comment line -- lets a CLI caller pass just the block's
    first line rather than pre-computing its extent by hand."""
    lines = file_text.splitlines()
    n = len(lines)
    if not (1 <= start_line <= n) or not lines[start_line - 1].lstrip().startswith("#"):
        return None
    end = start_line
    while end < n and lines[end].lstrip().startswith("#"):
        end += 1
    return (start_line, end)


# frob:ticket T-2995
# frob:doc docs/commands/narrative.md#usage
# frob:tests \
# tests/test_narrative_migrate.py::TestParagraphAt.test_finds_blank_line_delimited_para\
# graph
# frob:tests \
# tests/test_narrative_migrate.py::TestParagraphAt.test_blank_line_returns_none
def paragraph_at(file_text: str, start_line: int) -> tuple[int, int] | None:
    """The markdown-prose counterpart to `block_at` (T-2995): the `(start,
    end)` 1-indexed inclusive range of the contiguous non-blank paragraph
    beginning at `start_line`, or `None` if `start_line` is itself blank or
    out of range. Reuses `migrate_block`'s own comment-block engine below
    (no leading `#` required) rather than a second detector/migration
    path -- T-2994's doctrine applies identically to a doc paragraph
    citing a ticket id as it does to a `# T-####:` code comment."""
    lines = file_text.splitlines()
    n = len(lines)
    if not (1 <= start_line <= n) or not lines[start_line - 1].strip():
        return None
    end = start_line
    while end < n and lines[end].strip():
        end += 1
    return (start_line, end)
