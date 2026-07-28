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


def _archive(root: Path, *, force: bool = False) -> None:
    """Move every done/dropped ticket from the active ledger into
    tickets-archive.md, verbatim (idempotent -- a second run finds nothing
    to move). T-0810: `--force` threads through to `frob.tickets.archive`,
    overriding its T-0764 refusal when a live cross-worktree lease exists
    anywhere in the repo; a warning is logged so an override is never
    silent."""
    from frob.tickets import archive
    from frob.tickets._leases import read_all_leases

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
