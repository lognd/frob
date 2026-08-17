"""frob.app.ticket_runner._attach_backfill -- CLI dispatch for `frob ticket
attach --backfill-drafts` (T-2254).

T-2226 landed `frob.tickets._draft_finalize.backfill_stale_draft_attachment_
paths` (repairs `Attachment.path` fields a pre-T-2199 draft promotion left
dangling at a vanished `T-draft-<hash>` directory) with no way to invoke it:
four references, all inside its own defining module, no CLI parser, no
runner. T-2239 removed the CRLF corruption (`.gitattributes`) that made the
shared sha-reverify guard correctly refuse every repair attempt, so the
backfill can now actually relocate the two surviving `T-2195` records --
but only once it is reachable.

Wired onto the EXISTING `attach` verb (`--backfill-drafts`) rather than a
new subcommand -- T-2254's own constraint against inventing new vocabulary
when `frob ticket` already has `promote`/`attach`/`migrate`/`reconcile`.
`attach` is the closest fit: the `Attachment.path` record this backfill
repairs is squarely `attach`'s own domain, `promote`/`migrate` name
unrelated ledger-shape operations, and `reconcile` (T-0476) is a
narrowly-scoped worktree<->ticket binding healer whose own `reconcile()`
primitive has nothing to do with attachment records -- repurposing it would
misdescribe what the verb does, not just add a flag to it.

Split into its own sibling module (not a new function inside `_lifecycle.
py`, `_attach`'s home) because `_lifecycle.py` carried a live cross-
worktree lease (T-2220) for this ticket's entire duration -- `_attach_
dispatch` below decides which path to take and imports `_lifecycle._attach`
unmodified for the ordinary single-file case, so `_lifecycle.py` itself
needed zero edits."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

# Matches every sibling ticket_runner module's own logger name convention
# (`_lifecycle.py`/`_close_cmd.py`/... all use `get_logger("frob.app.
# ticket_runner")`, NOT the package-internal `frob.tickets`) -- this is
# also the exact logger name `run()`'s `_diagnostic_log_ctx` (T-0768)
# pins to INFO while clamping the rest of the `frob` tree to WARNING, so
# using any other name here would silently swallow every INFO line below
# at default verbosity.
_log = get_logger("frob.app.ticket_runner")


# frob:ticket T-2254
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts.test_backfill_drafts_dry_run_does_not_write  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketAttachBackfillDrafts.test_backfill_drafts_apply_writes_and_reports  # noqa: E501
def _attach_dispatch(root: Path, cfg: AppConfig) -> None:
    """`frob ticket attach` entry point (T-2254): routes to the draft-
    attachment backfill (`_run_backfill_drafts`) when `--backfill-drafts`
    is given, otherwise dispatches unchanged to `frob.app.ticket_runner.
    _lifecycle._attach`'s single-ticket attach-a-file behavior -- the
    ORIGINAL `attach` verb, byte-for-byte, for every caller that does not
    pass the new flag."""
    if cfg.ticket_attach_backfill_drafts:
        _run_backfill_drafts(root, cfg)
        return
    from frob.app.ticket_runner._lifecycle import _attach

    _attach(root, cfg)


def _run_backfill_drafts(root: Path, cfg: AppConfig) -> None:
    """T-2254: `frob ticket attach --backfill-drafts [--apply]` -- report
    (default, `dry_run=True`) or repair (`--apply`) every stale
    `T-draft-*`-prefixed attachment path in the CURRENT merged ledger via
    `backfill_stale_draft_attachment_paths`. Mirrors `frob ticket
    reconcile`'s report-first/`--apply`-to-write shape (T-2254 acceptance
    [5]'s dry-run requirement) rather than inventing a new flag
    convention for the same idea.

    Commits explicitly via `commit_full_ledger_change` -- the generic
    per-dispatch auto-commit (`_auto_commit_ledger_after_dispatch` in
    this package's `__init__.py`) is scoped to ONE `cfg.ticket_id`, which
    this repo-wide, ticket-id-less mode never sets; `commit_full_ledger_
    change` is the same whole-ledger-surface primitive `reconcile`/
    `archive` already use for exactly this reason (their own docstrings'
    precedent)."""
    from frob.tickets._draft_finalize import backfill_stale_draft_attachment_paths
    from frob.tickets._leases import commit_full_ledger_change

    apply = cfg.ticket_attach_backfill_apply
    result = backfill_stale_draft_attachment_paths(root, dry_run=not apply)
    if result.is_err:
        _log.error(
            "ticket attach --backfill-drafts: failed: %s", result.danger_err
        )
        sys.exit(1)
    report = result.danger_ok

    verb = "repaired" if apply else "would repair"
    _log.info(
        "ticket attach --backfill-drafts: %s %d stale draft attachment "
        "path(s): %s",
        verb,
        len(report.repaired),
        list(report.repaired),
    )
    if report.unresolved:
        _log.info(
            "ticket attach --backfill-drafts: %d unresolved (reported, "
            "left untouched, never guessed): %s",
            len(report.unresolved),
            list(report.unresolved),
        )
    if not apply:
        _log.info(
            "ticket attach --backfill-drafts: dry-run only, nothing "
            "written -- re-run with --apply to write these repairs"
        )
        return

    committed = commit_full_ledger_change(
        root,
        f"chore(tickets): backfill {len(report.repaired)} stale draft "
        "attachment path(s)",
        no_commit=cfg.ticket_no_commit,
    )
    if committed.is_err:
        _log.error(
            "ticket attach --backfill-drafts: ledger commit failed: %s",
            committed.danger_err,
        )
        sys.exit(1)
