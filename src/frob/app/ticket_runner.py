"""CLI wiring for `frob ticket new|list|show|doable|plan|start|sweep|attach|
block|close|fail` (docs/tickets.md)."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


# frob:doc docs/app.md#runners
def run(cfg: AppConfig) -> None:
    """Dispatch to the ticket subcommand named by `cfg.ticket_command`."""
    root = (cfg.ticket_path or Path(".")).resolve()

    match cfg.ticket_command:
        case "new":
            _new(root, cfg)
        case "list":
            _list(root, cfg)
        case "show":
            _show(root, cfg)
        case "doable":
            _doable(root, cfg)
        case "plan":
            _plan(root, cfg)
        case "start":
            _start(root, cfg)
        case "sweep":
            _sweep_cmd(root, cfg)
        case "migrate":
            _migrate(root)
        case "renumber":
            _renumber(root)
        case "attach":
            _attach(root, cfg)
        case "block":
            _block(root, cfg)
        case "close":
            _close(root, cfg)
        case "fail":
            _fail(root, cfg)
        case _:
            _log.error(
                "usage: frob ticket <new|list|show|doable|plan|start|sweep|"
                "attach|block|close|fail> ..."
            )
            sys.exit(1)


# frob:ticket T-0030
def _new(root: Path, cfg: AppConfig) -> None:
    # frob:ticket T-0005
    from frob.tickets import Origin, Stride, TicketKind, TicketSpec, new_ticket

    if cfg.ticket_title is None or cfg.ticket_kind is None:
        _log.error("frob ticket new requires --title and --kind")
        sys.exit(1)

    spec = TicketSpec(
        title=cfg.ticket_title,
        kind=TicketKind(cfg.ticket_kind),
        origin=Origin(cfg.ticket_origin) if cfg.ticket_origin else Origin.HUMAN,
        scope=tuple(cfg.ticket_scope),
        blocked_by=tuple(cfg.ticket_blocked_by),
        parent=cfg.ticket_parent,
        acceptance=tuple(cfg.ticket_acceptance),
        threat=Stride(cfg.ticket_threat) if cfg.ticket_threat else None,
        body=cfg.ticket_body,
    )
    result = new_ticket(root, spec)
    if result.is_err:
        _log.error("ticket new failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("created %s: %s", ticket.id, ticket.title)

    if sys.stdin.isatty():
        from frob.tickets import AttachmentSource, attach
        from frob.tickets.clipboard import clipboard_has_image

        if clipboard_has_image():
            answer = (
                input(f"Attach clipboard image to {ticket.id}? [y/N] ").strip().lower()
            )
            if answer == "y":
                attach_result = attach(
                    root, ticket.id, AttachmentSource(path=None), caption=""
                )
                if attach_result.is_err:
                    _log.error("clipboard attach failed: %s", attach_result.danger_err)
                else:
                    _log.info("attached clipboard image to %s", ticket.id)


def _filter_by_state(tickets, state):
    """Tickets whose state equals `state` (extracted so `_list` stays a flat
    sequence of independent steps, not a nested-loop join)."""
    return [t for t in tickets if t.state == state]


def _list(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import TicketState, load_queue

    result = load_queue(root)
    if result.is_err:
        _log.error("ticket list failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    tickets = sorted(queue.tickets.values(), key=lambda t: t.id)
    if cfg.ticket_state:
        tickets = _filter_by_state(tickets, TicketState(cfg.ticket_state))

    if cfg.ticket_json:
        import json

        _log.info(json.dumps([t.model_dump(mode="json") for t in tickets], indent=2))
        return

    if not tickets:
        _log.info("no tickets")
        return
    for t in tickets:
        _log.info("%s  [%s]  %s  (%s)", t.id, t.state.value, t.title, t.kind.value)


def _show(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import load_queue

    if cfg.ticket_id is None:
        _log.error("frob ticket show requires <id>")
        sys.exit(1)
    result = load_queue(root)
    if result.is_err:
        _log.error("ticket show failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None:
        _log.error("no ticket %s", cfg.ticket_id)
        sys.exit(1)

    if cfg.ticket_json:
        _log.info(ticket.model_dump_json(indent=2))
        return

    _log.info(
        "%s  [%s]  %s  (%s)\nblocked_by=%s scope=%s\n\n%s",
        ticket.id,
        ticket.state.value,
        ticket.title,
        ticket.kind.value,
        list(ticket.blocked_by),
        list(ticket.scope),
        ticket.body,
    )


def _doable(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import doable, load_queue

    result = load_queue(root)
    if result.is_err:
        _log.error("ticket doable failed: %s", result.danger_err)
        sys.exit(1)
    tickets = doable(result.danger_ok)

    if cfg.ticket_json:
        import json

        _log.info(json.dumps([t.model_dump(mode="json") for t in tickets], indent=2))
        return

    if not tickets:
        _log.info("nothing doable")
        return
    for t in tickets:
        _log.info("%s  %s  (%s)", t.id, t.title, t.kind.value)


def _migrate(root: Path) -> None:
    from frob.tickets import migrate

    result = migrate(root)
    if result.is_err:
        _log.error("ticket migrate failed: %s", result.danger_err)
        sys.exit(1)
    n = result.danger_ok
    if n == 0:
        _log.info("no legacy tickets/*.md files to migrate")
    else:
        _log.info("migrated %d ticket(s) into tickets.md; removed tickets/*.md", n)


def _renumber(root: Path) -> None:
    # frob:ticket T-0012
    from frob.tickets import renumber

    result = renumber(root)
    if result.is_err:
        _log.error("ticket renumber failed: %s", result.danger_err)
        sys.exit(1)
    n = result.danger_ok
    if n:
        _log.info("renumbered %d ticket(s)", n)
    else:
        _log.info("ids already contiguous")


def _plan(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket plan requires <id>")
        sys.exit(1)
    planned = transition(root, cfg.ticket_id, TicketState.PLANNED)
    if planned.is_err:
        _log.error("ticket plan failed: %s", planned.danger_err)
        sys.exit(1)
    _log.info("planned %s", cfg.ticket_id)


def _start(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import TicketState, load_queue, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket start requires <id>")
        sys.exit(1)

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("ticket start failed: %s", queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None:
        _log.error("no ticket %s", cfg.ticket_id)
        sys.exit(1)

    # `start` from a fresh ticket walks queued -> planned -> in-progress; the
    # state machine stays strict, the CLI just takes both legal steps.
    if ticket.state == TicketState.QUEUED:
        planned = transition(root, cfg.ticket_id, TicketState.PLANNED)
        if planned.is_err:
            _log.error("ticket start failed: %s", planned.danger_err)
            sys.exit(1)
        _log.info("auto-planned %s (queued -> planned)", cfg.ticket_id)
        ticket = planned.danger_ok

    transitioned = transition(root, cfg.ticket_id, TicketState.IN_PROGRESS)
    if transitioned.is_err:
        _log.error("ticket start failed: %s", transitioned.danger_err)
        sys.exit(1)

    _run_sweep(root, transitioned.danger_ok)


def _sweep_cmd(root: Path, cfg: AppConfig) -> None:
    """Re-record the pre-work sweep for an in-progress ticket (scope widened)."""
    from frob.tickets import TicketState, load_queue

    if cfg.ticket_id is None:
        _log.error("frob ticket sweep requires <id>")
        sys.exit(1)
    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("ticket sweep failed: %s", queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None:
        _log.error("no ticket %s", cfg.ticket_id)
        sys.exit(1)
    if ticket.state != TicketState.IN_PROGRESS:
        _log.error("ticket sweep: %s is not in-progress", cfg.ticket_id)
        sys.exit(1)
    _run_sweep(root, ticket)


def _run_sweep(root: Path, ticket) -> None:
    """Record the pre-work sweep (dup + xref + scope digest) for `ticket`.

    The digest MUST come from frob.gates.scope_digest -- the gate compares
    against the same function, so recording and checking can never desync.
    """
    from frob.dup import find_duplicates
    from frob.gates import PreworkSweep, record_prework, scope_digest
    from frob.graph import build_graph, load_graph
    from frob.xref import xref

    dup_result = find_duplicates(root)
    dup_findings = dup_result.total_clones

    xref_hits: list[str] = []
    scope = ticket.scope or (".",)
    for pattern in scope:
        base = pattern.split("*", 1)[0].rstrip("/") or "."
        scan_path = root / base if base != "." else root
        if not scan_path.exists():
            continue
        symbol = Path(pattern).stem
        xref_result = xref(symbol, root)
        if xref_result.is_ok:
            xref_hits.append(xref_result.danger_ok.symbol)

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        loaded = build_graph(root, cache)
    digest = scope_digest(ticket.scope, loaded.danger_ok) if loaded.is_ok else ""

    sweep = PreworkSweep(
        date=date.today(),
        dup_findings=dup_findings,
        xref_hits=tuple(xref_hits),
        digest=digest,
    )
    recorded = record_prework(root, ticket.id, sweep)
    if recorded.is_err:
        _log.error("pre-work sweep recording failed: %s", recorded.danger_err)
        sys.exit(1)

    _log.info(
        "swept %s: dup_findings=%d xref_hits=%d",
        ticket.id,
        dup_findings,
        len(xref_hits),
    )


def _attach(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import AttachmentSource, attach

    if cfg.ticket_id is None:
        _log.error("frob ticket attach requires <id>")
        sys.exit(1)

    source = AttachmentSource(path=cfg.ticket_attach_path)
    result = attach(root, cfg.ticket_id, source, caption=cfg.ticket_caption)
    if result.is_err:
        _log.error("attach failed: %s", result.danger_err)
        sys.exit(1)
    attachment = result.danger_ok
    _log.info("attached %s (sha256=%s)", attachment.path, attachment.sha256)


def _block(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import _load_one
    from frob.tickets._store import write_ticket

    if cfg.ticket_id is None or cfg.ticket_by is None:
        _log.error("frob ticket block requires <id> and --by")
        sys.exit(1)

    loaded = _load_one(root, cfg.ticket_id)
    if loaded.is_err:
        _log.error("block failed: %s", loaded.danger_err)
        sys.exit(1)
    ticket = loaded.danger_ok
    updated = ticket.model_copy(
        update={"blocked_by": ticket.blocked_by + (cfg.ticket_by,)}
    )
    written = write_ticket(root, updated)
    if written.is_err:
        _log.error("block failed: %s", written.danger_err)
        sys.exit(1)
    _log.info("%s now blocked by %s", cfg.ticket_id, cfg.ticket_by)


def _close(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket close requires <id>")
        sys.exit(1)
    result = transition(root, cfg.ticket_id, TicketState.DONE)
    if result.is_err:
        _log.error("close failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s closed (done)", cfg.ticket_id)


def _fail(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import FailureEntry, load_queue, record_failure

    if cfg.ticket_id is None or cfg.ticket_summary is None:
        _log.error("frob ticket fail requires <id> and --summary")
        sys.exit(1)

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("fail failed: %s", queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(cfg.ticket_id)
    if ticket is None:
        _log.error("no ticket %s", cfg.ticket_id)
        sys.exit(1)

    attempt = ticket.body.count("attempt ") + 1
    entry = FailureEntry(date=date.today(), attempt=attempt, summary=cfg.ticket_summary)
    result = record_failure(root, cfg.ticket_id, entry)
    if result.is_err:
        _log.error("fail failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s: recorded failure attempt %d", cfg.ticket_id, attempt)
