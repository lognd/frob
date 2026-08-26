"""frob.narrative -- T-2993's detector plus author-invoked migration verb
for `# T-####:` narrative comment blocks.

Two halves, deliberately not fused into `land` (T-2994's own doctrine:
land may CHECK, never REWRITE):

- `frob.gates._narrative_blocks` (NARR001) flags candidate blocks so the
  pattern cannot regrow silently.
- `frob.narrative._migrate` moves one block's narrative text into the
  ticket it already names, leaving a one-line reference in place --
  invoked by an author/agent as `frob narrative move`, never by `land`.
"""

from __future__ import annotations

from frob.narrative._cli import add_narrative_parser, run_narrative_command
from frob.narrative._migrate import (
    MigrateError,
    MigrationResult,
    block_at,
    migrate_block,
    moved_text_for_ticket,
    split_ticket_id,
)

__all__ = [
    "MigrateError",
    "MigrationResult",
    "add_narrative_parser",
    "block_at",
    "migrate_block",
    "moved_text_for_ticket",
    "run_narrative_command",
    "split_ticket_id",
]
