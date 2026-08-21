"""frob.tickets._store_migrate -- the one-shot, reversible v1<->v2 ledger
migration functions (T-1259/T-2355), split out of `frob.tickets._store`
(T-2695, LARGE001 remainder batch 2).

SEAM: `_store.py` is steady-state storage -- read/write/lock a ledger or
v2 tree that already exists in its current mode. Every function below is
instead a ONE-SHOT CONVERSION between two on-disk representations
(legacy dir-mode -> monofile ledger, v1 monofile -> v2 per-ticket tree, or
filling the v2-partial-migration gap `migrate_v1_to_v2` leaves open) --
invoked from `frob ticket migrate`/`frob ticket archive`, never from the
steady-state read/write hot path `_store.py` itself still owns. That is a
real distinct-consumer-set split (T-1656/T-1651's own "cohesive
responsibility, pipeline phase, distinct consumer set" test): the CLI
migrate command and its own test suite (`tests/test_tickets_migration.py`)
are this module's only real callers, not the ticket read/write callers
`_store.py`'s remaining ~2300 lines serve.

IMPORT SHAPE: every `frob.tickets._store` primitive this module needs
(`atomic_write`, path helpers, ledger parse/serialize, `git_mv_dir`) is
imported FUNCTION-LOCAL, never at module top level -- `_store.py` in turn
imports this module's public migrate functions at ITS top level, for
re-export (same T-1089/T-0395 tier-2-split convention every other
private-module split in this repo uses, so every existing
`frob.tickets._store.<name>` call site -- `_archive.py`, `_setters.py`,
`_query.py`, every test importing `from frob.tickets._store import
migrate_*` -- keeps working with no caller-side change). A module-level
`from frob.tickets._store import ...` here would be a genuine import
cycle (`_store` -> `_store_migrate` -> `_store`); the function-local
import is this repo's own standing convention for exactly this shape
(see `_land_cmd.py`/`_check_chunking.py`'s own cross-module helper
imports), not a one-off workaround."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from typani.result import Err, Ok, Result

from frob.logging import get_logger
from frob.tickets._models import (
    Ticket,
    TicketError,
    _done_report_section_end,
    _find_done_report_heading,
)

_log = get_logger(__name__)


# frob:ticket T-2695
# frob:doc docs/modules/tickets-data-storage.md#storage-internals
# frob:tests tests/unit/test_ticket_store.py::TestMigrateToLedger.test_moves_legacy_files_into_ledger  # noqa: E501
# frob:tests tests/unit/test_store_batch7.py::TestMigrateToLedger.test_atomic_write_failure_propagates  # noqa: E501
# frob:waive AFFECT001 follow_up="T-2730" reason="pure code relocation (LARGE001 \
# remainder batch 2, extracted verbatim from _store.py) -- the doc content this \
# function affects is unchanged, only the source file path moved; the doc itself \
# (docs/modules/tickets-data-storage.md) is under another ticket's LIVE lease (T-2718) \
# at the time of this extraction, so it cannot be edited here"
def migrate_to_ledger(root: Path) -> Result[int, TicketError]:
    """Collapse a legacy tickets/*.md layout into a single tickets.md ledger.

    Reads every dir-mode ticket, writes the ledger, then deletes the source
    files. Attachments under tickets/attachments/ are left untouched (both
    modes share that location). Returns the number of tickets migrated.
    """
    from frob.tickets._store import (
        _dir_glob,
        _parse_ticket_file,
        _render_ledger,
        atomic_write,
        ledger_path,
    )

    files = _dir_glob(root)
    if not files:
        return Ok(0)
    tickets: dict[str, Ticket] = {}
    for path in files:
        parsed = _parse_ticket_file(path)
        if parsed.is_err:
            return Err(parsed.danger_err)
        tickets[parsed.danger_ok.id] = parsed.danger_ok
    written = atomic_write(ledger_path(root), _render_ledger(tickets))
    if written.is_err:
        return Err(written.danger_err)
    for path in files:
        try:
            path.unlink()
        except OSError as exc:
            _log.warning("tickets: could not remove migrated %s: %s", path, exc)
    _log.info("tickets: migrated %d ticket(s) into %s", len(tickets), ledger_path(root))
    return Ok(len(tickets))


# frob:ticket T-1259
# frob:ticket T-2695
# frob:doc \
# docs/modules/tickets-data-storage.md#migration-to-v2-t-1259-docsdesignledger-v2md-sec\
# tion-7
# frob:waive AFFECT001 follow_up="T-2730" reason="pure code relocation (LARGE001 \
# remainder batch 2, extracted verbatim from _store.py) -- the doc content this \
# function affects is unchanged, only the source file path moved; the doc itself \
# (docs/modules/tickets-data-storage.md) is under another ticket's LIVE lease (T-2718) \
# at the time of this extraction, so it cannot be edited here"
def _split_done_report(body: str) -> tuple[str, str | None]:
    """Split a v1-mode ticket `body` into (body_without_done_report,
    done_report_text_or_None), the mechanical inverse of `_models.
    replace_done_report_section`'s splice: v1 embeds the '## Done report'
    section inside the same body block `_render_ledger` writes; v2 stores
    it in its own `done-report.md` (design section 1). Reuses `_models`'s
    own heading/section-boundary scan (`_find_done_report_heading`/
    `_done_report_section_end`) rather than re-deriving the same T-0493/
    T-0848 boundary logic a second time -- the section runs from a genuine
    `## Done report` heading through the next structural heading or EOF,
    exactly what `replace_done_report_section` itself treats as
    replaceable. Returns `(body, None)` unchanged if `body` carries no Done
    report section at all (a queued/in-progress ticket)."""
    lines = body.splitlines()
    heading_idx = _find_done_report_heading(lines)
    if heading_idx is None:
        return body, None
    end_idx = _done_report_section_end(lines, heading_idx)
    report_lines = lines[heading_idx:end_idx]
    remaining = lines[:heading_idx] + lines[end_idx:]
    while remaining and remaining[-1] == "":
        remaining.pop()
    report_text = "\n".join(report_lines).strip("\n") + "\n"
    new_body = "\n".join(remaining)
    return new_body, report_text


# frob:ticket T-1259
# frob:ticket T-2695
# frob:doc \
# docs/modules/tickets-data-storage.md#migration-to-v2-t-1259-docsdesignledger-v2md-sec\
# tion-7
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_migrates_one_active_ticket_with_done_report  # noqa: E501
# frob:waive AFFECT001 follow_up="T-2730" reason="pure code relocation (LARGE001 \
# remainder batch 2, extracted verbatim from _store.py) -- the doc content this \
# function affects is unchanged, only the source file path moved; the doc itself \
# (docs/modules/tickets-data-storage.md) is under another ticket's LIVE lease (T-2718) \
# at the time of this extraction, so it cannot be edited here"
def _migrate_one_v2(
    root: Path, ticket: Ticket, dest_dir: Path
) -> Result[None, TicketError]:
    """Write one v1-mode `ticket` into a v2-mode `dest_dir` (an active
    `tickets/T-####/` or archived `tickets/archive/T-####/` directory,
    caller's choice): splits the embedded Done report out of `ticket.body`
    into `dest_dir/done-report.md` (`_split_done_report`), writes the
    remaining frontmatter+body to `dest_dir/ticket.md`, and `git mv`s any
    legacy `tickets/attachments/<id>/` directory to `dest_dir/attachments/`
    (design section 7's "moved attachments" deliverable) via the same
    `git_mv_dir` primitive `archive_v2` already uses."""
    from frob.tickets._store import (
        _serialize_ticket,
        atomic_write,
        attachments_dir,
        git_mv_dir,
    )

    new_body, report_text = _split_done_report(ticket.body)
    migrated = ticket.model_copy(update={"body": new_body})
    written = atomic_write(dest_dir / "ticket.md", _serialize_ticket(migrated))
    if written.is_err:
        return Err(written.danger_err)
    if report_text is not None:
        report_written = atomic_write(dest_dir / "done-report.md", report_text)
        if report_written.is_err:
            return Err(report_written.danger_err)
    legacy_attachments = attachments_dir(root, ticket.id)
    if legacy_attachments.is_dir() and any(legacy_attachments.iterdir()):
        moved = git_mv_dir(root, legacy_attachments, dest_dir / "attachments")
        if moved.is_err:
            return Err(moved.danger_err)
    return Ok(None)


# frob:ticket T-1259
# frob:ticket T-2695
# frob:doc \
# docs/modules/tickets-data-storage.md#migration-to-v2-t-1259-docsdesignledger-v2md-sec\
# tion-7
# frob:doc docs/modules/tickets-data-storage.md#storage-internals
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_golden_round_trip_semantic_equality  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_idempotent_no_v1_state_is_a_no_op  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateV1ToV2.test_draft_id_ticket_migrates_like_any_other  # noqa: E501
# frob:waive AFFECT001 follow_up="T-2730" reason="pure code relocation (LARGE001 \
# remainder batch 2, extracted verbatim from _store.py) -- the doc content this \
# function affects is unchanged, only the source file path moved; the doc itself \
# (docs/modules/tickets-data-storage.md) is under another ticket's LIVE lease (T-2718) \
# at the time of this extraction, so it cannot be edited here"
def migrate_v1_to_v2(root: Path) -> Result[int, TicketError]:
    """One-shot, reversible migrator (ledger v2 design section 7,
    deliverable 1): reads today's `tickets.md`/`tickets-archive.md` via
    `_parse_ledger`, writes each ticket into a v2-mode `tickets/T-####/
    ticket.md` (+ `done-report.md`, + a moved `attachments/`), WITHOUT
    deleting the monofile ledgers in the same call -- rolling back is
    `rm -rf tickets/T-*/ tickets/archive/` while `tickets.md`/`tickets-
    archive.md` are still exactly as they were (nothing here ever writes
    to either path).

    A no-op (`Ok(0)`) if the repo is already v2-mode (`_store_mode`) --
    migrate is safe to invoke repeatedly. Returns the number of tickets
    migrated (active + archived), mirroring `migrate_to_ledger`'s own
    return-count convention."""
    from frob.tickets._store import (
        _parse_ledger,
        _store_mode,
        archive_path,
        ledger_path,
        v2_archive_dir,
        v2_ticket_dir,
    )

    if _store_mode(root) == "v2":
        _log.info("tickets: already v2-mode, nothing to migrate")
        return Ok(0)
    active: dict[str, Ticket] = {}
    active_path = ledger_path(root)
    if active_path.exists():
        parsed = _parse_ledger(active_path.read_text(encoding="utf-8"))
        if parsed.is_err:
            return Err(parsed.danger_err)
        active = parsed.danger_ok
    archived: dict[str, Ticket] = {}
    archive_p = archive_path(root)
    if archive_p.exists():
        parsed = _parse_ledger(archive_p.read_text(encoding="utf-8"))
        if parsed.is_err:
            return Err(parsed.danger_err)
        archived = parsed.danger_ok
    for ticket_id, ticket in active.items():
        result = _migrate_one_v2(root, ticket, v2_ticket_dir(root, ticket_id))
        if result.is_err:
            return Err(result.danger_err)
    for ticket_id, ticket in archived.items():
        result = _migrate_one_v2(root, ticket, v2_archive_dir(root, ticket_id))
        if result.is_err:
            return Err(result.danger_err)
    total = len(active) + len(archived)
    _log.info(
        "tickets: migrated %d ticket(s) to v2 layout (%d active, %d archived); "
        "tickets.md/tickets-archive.md left in place -- delete tickets/T-*/ "
        "tickets/archive/ to roll back",
        total,
        len(active),
        len(archived),
    )
    return Ok(total)


# frob:ticket T-2355
# frob:ticket T-2695
# frob:doc docs/design/ledger-v2.md#7-reversible-migration-plan-design-for-the-child-ticket-not-built-here  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateMissingV2.test_migrates_only_the_monofile_only_tickets  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateMissingV2.test_never_overwrites_an_already_migrated_ticket  # noqa: E501
# frob:tests tests/test_tickets_migration.py::TestMigrateMissingV2.test_a_stale_active_row_whose_v2_state_already_moved_to_archive_is_not_duplicated  # noqa: E501
# frob:waive AFFECT001 follow_up="T-2730" reason="pure code relocation (LARGE001 \
# remainder batch 2, extracted verbatim from _store.py) -- the doc content this \
# function affects is unchanged, only the source file path moved; the doc itself \
# (docs/modules/tickets-data-storage.md) is under another ticket's LIVE lease (T-2718) \
# at the time of this extraction, so it cannot be edited here"
# frob:waive WIRE001 follow_up="T-2728" reason="pre-existing (T-2355): no CLI wiring \
# for this function anywhere in src/frob/_cli_parsers or src/frob/app -- confirmed by \
# direct search, only reachable from tests today. T-2695's own extraction (LARGE001 \
# remainder batch 2) surfaced this as a fresh finding (diff-based novelty heuristic), \
# not new debt from the move itself"
def migrate_missing_v2(root: Path) -> Result[int, TicketError]:
    """Partial-migration gap `migrate_v1_to_v2` cannot close (T-2355):
    that migrator no-ops entirely (`Ok(0)`) the instant `_store_mode`
    reads `"v2"` (any `tickets/T-####/ticket.md` at all), so a repo that
    was cut over to v2 for NEW writes but still carries legacy tickets
    that exist ONLY in `tickets.md`/`tickets-archive.md` (never
    individually migrated -- design section 7's confirmation-and-delete
    step was never run for them) has no path to a real per-ticket file
    for those ids at all.

    For every id `_parse_ledger` finds in the monofile ledger/archive
    that does NOT already have a `tickets/T-####/ticket.md` OR a
    `tickets/archive/T-####/ticket.md` -- checked in BOTH v2 locations
    regardless of which monofile the id's row came from, since a stale
    "active" row can already be migrated into the ARCHIVE side (the
    ticket moved on after an earlier individual migration; live incident
    during T-2355's own implementation: measuring "missing" against only
    the row's own claimed side produced 108 apparent gaps that were
    every one of them already-archived v2 tickets, and writing them again
    as "active" tripped `frob check`'s DuplicateId gate) -- writes one via
    `_migrate_one_v2` into the location the monofile row's own state
    implies, identical per-ticket output to `migrate_v1_to_v2`, just
    reachable when the repo is already v2-mode. An id that already has a
    v2 file ANYWHERE is left untouched, byte for byte -- this function
    only ever ADDS a genuinely missing file, never overwrites or
    re-derives an existing one (T-2355 acceptance: an already-migrated
    ticket's state may have diverged from its stale monofile row since
    migration, and that current v2 state is authoritative, not the
    monofile's snapshot). Monofiles are never written to or deleted here,
    same reversibility guarantee as `migrate_v1_to_v2`. Returns the count
    of ids actually written."""
    from frob.tickets._store import (
        _parse_ledger,
        archive_path,
        ledger_path,
        v2_archive_dir,
        v2_ticket_dir,
    )

    active: dict[str, Ticket] = {}
    active_path = ledger_path(root)
    if active_path.exists():
        parsed = _parse_ledger(active_path.read_text(encoding="utf-8"))
        if parsed.is_err:
            return Err(parsed.danger_err)
        active = parsed.danger_ok
    archived: dict[str, Ticket] = {}
    archive_p = archive_path(root)
    if archive_p.exists():
        parsed = _parse_ledger(archive_p.read_text(encoding="utf-8"))
        if parsed.is_err:
            return Err(parsed.danger_err)
        archived = parsed.danger_ok

    active_written = _migrate_missing_ids(root, active, v2_ticket_dir)
    if active_written.is_err:
        return Err(active_written.danger_err)
    archived_written = _migrate_missing_ids(root, archived, v2_archive_dir)
    if archived_written.is_err:
        return Err(archived_written.danger_err)

    written = active_written.danger_ok + archived_written.danger_ok
    _log.info(
        "tickets: migrate_missing_v2 wrote %d monofile-only ticket(s) into v2 "
        "layout; every already-migrated ticket left untouched",
        written,
    )
    return Ok(written)


# frob:ticket T-2695
def _migrate_missing_ids(
    root: Path,
    tickets: dict[str, Ticket],
    home_dir: Callable[[Path, str], Path],
) -> Result[int, TicketError]:
    """`migrate_missing_v2`'s per-map body, split out to keep the caller
    under ARCH001's line threshold: writes `home_dir(root, id)` for every
    `tickets` entry that has no v2 file yet in EITHER v2 location
    (`v2_ticket_dir` or `v2_archive_dir`) -- checked in both regardless of
    which monofile `tickets` came from, since a monofile row's own
    claimed side (active vs archived) can be stale relative to where the
    ticket's v2 state actually lives (T-2355 incident: a stale 'active'
    row whose v2 state had already moved to `tickets/archive/<id>/`
    produced a genuine duplicate id when only `home_dir` itself was
    checked). Returns the count actually written."""
    from frob.tickets._store import v2_archive_dir, v2_ticket_dir

    written = 0
    for ticket_id, ticket in tickets.items():
        if (v2_ticket_dir(root, ticket_id) / "ticket.md").exists():
            continue
        if (v2_archive_dir(root, ticket_id) / "ticket.md").exists():
            continue
        result = _migrate_one_v2(root, ticket, home_dir(root, ticket_id))
        if result.is_err:
            return Err(result.danger_err)
        written += 1
    return Ok(written)
