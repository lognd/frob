"""frob.app.ticket_runner._archive -- the `archive` command.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.tickets._leases import _LeaseRecord

_log = get_logger("frob.app.ticket_runner")


# frob:ticket T-1762
def _resolve_force_reason(
    reason: str | None, reason_file: Path | None, *, cli_label: str
) -> str | None:
    """Resolve `--force`'s paired `--reason`/`--reason-file` (T-1762, the
    `frob ticket scope --reason` precedent applied to `--force`):
    `--reason-file` wins if given (read verbatim via `frob.app.ticket_
    runner._mutate.read_reason_file_verbatim`, T-0737), else the inline
    `--reason` string. Exits 1 if both are given; returns `None` if
    neither is given (the caller decides whether that is an error --
    `--force` with no live guard to override is a no-op, so `_archive`
    only requires a reason when the guard actually fires)."""
    from frob.app.ticket_runner._mutate import read_reason_file_verbatim

    if reason_file is not None and reason:
        _log.error("%s: --reason and --reason-file are mutually exclusive", cli_label)
        sys.exit(1)
    if reason_file is not None:
        return read_reason_file_verbatim(reason_file, cli_label=cli_label)
    return reason


# frob:ticket T-1762
def _require_archive_force_reason(
    live_leases: Sequence["_LeaseRecord"],
    force_reason: str | None,
    force_reason_file: Path | None,
) -> str:
    """Resolve `--force`'s reason via `_resolve_force_reason`, or
    `sys.exit(1)` naming the live leases it would otherwise refuse
    (T-1762) -- split from the record half to stay under ARCH103's
    per-body decision-point budget."""
    reason = _resolve_force_reason(
        force_reason, force_reason_file, cli_label="ticket archive"
    )
    if not reason:
        _log.error(
            "ticket archive --force requires --reason TEXT or --reason-file "
            "PATH (T-1762): %d live cross-worktree lease(s) would otherwise "
            "refuse this archive",
            len(live_leases),
        )
        sys.exit(1)
    return reason


# frob:ticket T-1762
def _record_or_refuse_archive_force(
    root: Path,
    live_leases: Sequence["_LeaseRecord"],
    force_reason: str | None,
    force_reason_file: Path | None,
) -> None:
    """`_require_reason_for_archive_force`'s reason-resolve/record half:
    `_require_archive_force_reason` resolves (or refuses for) the reason,
    then `record_force_override` records the override -- `sys.exit(1)` on
    a record failure too, an unrecorded forced archive is not an
    acceptable outcome."""
    from frob.tickets._force_override import record_force_override

    reason = _require_archive_force_reason(live_leases, force_reason, force_reason_file)
    recorded = record_force_override(
        root,
        command="ticket archive",
        guard="T-0843 live-cross-worktree-lease refusal",
        target=",".join(sorted(lease.ticket_id for lease in live_leases)),
        reason=reason,
    )
    if recorded.is_err:
        _log.error("ticket archive --force: %s", recorded.danger_err)
        sys.exit(1)


# frob:ticket T-1615
# frob:ticket T-1762
def _require_reason_for_archive_force(
    root: Path,
    force: bool,
    force_reason: str | None,
    force_reason_file: Path | None,
) -> None:
    """`_archive`'s T-1762 force-reason gate, split out to stay under
    ARCH001/ARCH103's per-body budget: a no-op unless `force` is set AND a
    live cross-worktree lease actually exists (the guard would otherwise
    have refused) -- the reason-resolve/record half is
    `_record_or_refuse_archive_force`."""
    from frob.tickets._leases import read_all_leases

    if not force:
        return
    live_leases = read_all_leases(root)
    if not live_leases:
        return
    _record_or_refuse_archive_force(root, live_leases, force_reason, force_reason_file)


def _archive(
    root: Path,
    *,
    force: bool = False,
    no_commit: bool = False,
    force_reason: str | None = None,
    force_reason_file: Path | None = None,
) -> None:
    """Move every done/dropped ticket from the active ledger into
    tickets-archive.md, verbatim (idempotent -- a second run finds nothing
    to move). T-0810: `--force` threads through to `frob.tickets.archive`,
    overriding its T-0764 refusal when a live cross-worktree lease exists
    anywhere in the repo.

    T-1762: when `force=True` AND a live lease actually exists (the guard
    would otherwise have refused), a reason is now REQUIRED (see
    `_require_reason_for_archive_force`) -- and the override is recorded
    via `frob.tickets._force_override.record_force_override` (WARNING log
    + an append-only `force-overrides.jsonl` line) before `archive` runs.
    `--force` with no live lease to override is a no-op guard-wise, so no
    reason is demanded for it (nothing was actually bypassed).

    T-1615: auto-commits the whole-ledger change afterward
    (`commit_full_ledger_change` -- `archive` moves potentially MANY
    tickets in one call, not one ticket id, so the single-ticket `frob.
    app.ticket_runner._auto_commit_ledger_after_dispatch` wrapper every
    OTHER verb goes through cannot cover it; this is its own explicit
    call site instead). `--no-commit` (`no_commit`) opts out, warning
    loudly if it leaves the ledger dirty, same contract as every other
    ledger-mutating verb."""
    from frob.tickets import archive
    from frob.tickets._leases import commit_full_ledger_change

    _require_reason_for_archive_force(root, force, force_reason, force_reason_file)

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


# frob:ticket T-2954
# frob:tests \
# tests/unit/test_ticket_restore.py::TestRestoreCli.test_restore_cli_wiring_delegates_a\
# nd_commits
def _restore(root: Path, cfg) -> None:  # noqa: ANN001
    """CLI wiring for `frob ticket restore <id> --reason TEXT` (T-2954):
    the repair verb for a ticket stranded under `tickets/archive/` in a
    non-terminal state (T-0450's own incident). Delegates entirely to
    `frob.tickets.restore` for the git-mv + attachment-path-reverse +
    `## Restore log` write; this layer only validates required args and
    reports the Result -- the same thin-wiring shape `_reopen` already
    uses for `reopen_ticket`.

    T-2954: commits via `commit_full_ledger_change` (the WHOLE-ledger
    pathspec form), never the single-ticket `commit_ticket_ledger_
    change` -- `restore`'s `git mv` touches TWO distinct pathspecs at
    once (`tickets/archive/<id>` vacated, `tickets/<id>` created), and
    `_ledger_pathspecs(root, ticket_id)`'s exists-check would only ever
    return the NEW path (the vacated archive directory no longer exists
    on disk to be found), leaving `git commit -- tickets/<id>` alone: the
    archive-side deletion `git mv` already staged in the index falls
    OUTSIDE that pathspec and would be left committed-nowhere, a
    genuinely dirty tree straight out of a 'successful' restore -- the
    exact class `archive`'s own CLI wiring (`_archive`, this same file)
    already avoids by using `commit_full_ledger_change` for its own
    multi-path `git mv` sweep."""
    from frob.tickets import restore
    from frob.tickets._leases import commit_full_ledger_change

    if cfg.ticket_id is None or not cfg.ticket_reason:
        _log.error("frob ticket restore requires <id> and --reason")
        sys.exit(1)

    result = restore(root, cfg.ticket_id, reason=cfg.ticket_reason)
    if result.is_err:
        _log.error("restore failed: %s", result.danger_err)
        sys.exit(1)
    restored = result.danger_ok
    _log.info(
        "%s restored (tickets/archive/%s -> tickets/%s, state=%s)",
        cfg.ticket_id,
        cfg.ticket_id,
        cfg.ticket_id,
        restored.state.value,
    )

    committed = commit_full_ledger_change(
        root,
        f"chore(tickets): restore {cfg.ticket_id}",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        sys.exit(1)
