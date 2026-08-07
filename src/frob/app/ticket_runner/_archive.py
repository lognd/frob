"""frob.app.ticket_runner._archive -- the `archive` command.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.logging import get_logger

_log = get_logger("frob.app.ticket_runner")


# frob:ticket T-1615
def _archive(root: Path, *, force: bool = False, no_commit: bool = False) -> None:
    """Move every done/dropped ticket from the active ledger into
    tickets-archive.md, verbatim (idempotent -- a second run finds nothing
    to move). T-0810: `--force` threads through to `frob.tickets.archive`,
    overriding its T-0764 refusal when a live cross-worktree lease exists
    anywhere in the repo; a warning is logged so an override is never
    silent.

    T-1615: auto-commits the whole-ledger change afterward
    (`commit_full_ledger_change` -- `archive` moves potentially MANY
    tickets in one call, not one ticket id, so the single-ticket `frob.
    app.ticket_runner._auto_commit_ledger_after_dispatch` wrapper every
    OTHER verb goes through cannot cover it; this is its own explicit
    call site instead). `--no-commit` (`no_commit`) opts out, warning
    loudly if it leaves the ledger dirty, same contract as every other
    ledger-mutating verb."""
    from frob.tickets import archive
    from frob.tickets._leases import commit_full_ledger_change, read_all_leases

    if force:
        live_leases = read_all_leases(root)
        if live_leases:
            _log.warning(
                "ticket archive --force: overriding %d live cross-worktree "
                "lease(s) -- archiving anyway",
                len(live_leases),
            )

    result = archive(root, force=force)
    if result.is_err:
        _log.error("ticket archive failed: %s", result.danger_err)
        sys.exit(1)
    n = result.danger_ok
    if n == 0:
        _log.info("nothing to archive")
    else:
        _log.info("archived %d ticket(s) into tickets-archive.md", n)

    committed = commit_full_ledger_change(
        root, f"chore(tickets): archive {n} ticket(s)", no_commit=no_commit
    )
    if committed.is_err:
        sys.exit(1)
