"""CLI wiring for `frob ticket new|list|show|doable|plan|start|sweep|land|
attach|block|close|fail|evidence|archive` (docs/modules/tickets.md)."""

# frob:waive TEST005 reason="module line coverage 22.7%, debt T-0160"

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from frob.app._style import style_state, style_ticket_id
from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

_CACHE_REL = Path(".frob") / "cache.db"


def _stdout_color() -> bool:
    """Whether ticket-listing lines (routed to stdout via `_log.info`,
    `frob.logging.config.toml`'s below-WARNING handler) should carry ANSI
    color -- T-0179's single should_color(stdout) check, evaluated once per
    call site rather than duplicated per print."""
    from frob.logging.color import should_color

    return should_color(sys.stdout)


def _ticket_dispatch_table() -> dict:
    """Map each `frob ticket` subcommand name to its `(root, cfg)` handler."""
    return {
        "new": _new,
        "list": _list,
        "show": _show,
        "doable": _doable,
        "plan": _plan,
        "start": _start,
        "sweep": _sweep_cmd,
        "migrate": lambda root, _cfg: _migrate(root),
        "renumber": _renumber,
        "land": _land,
        "attach": _attach,
        "block": _block,
        "close": _close,
        "fail": _fail,
        "evidence": _evidence,
        "archive": lambda root, _cfg: _archive(root),
    }


# frob:doc docs/modules/app.md#runners
# frob:waive TEST005 reason="run 20.0% branch cover, debt T-0160"
def run(cfg: AppConfig) -> None:
    """Dispatch to the ticket subcommand named by `cfg.ticket_command`."""
    root = (cfg.ticket_path or Path(".")).resolve()

    handler = _ticket_dispatch_table().get(cfg.ticket_command)
    if handler is None:
        _log.error(
            "usage: frob ticket <new|list|show|doable|plan|start|sweep|"
            "land|attach|block|close|fail|evidence|archive> ..."
        )
        sys.exit(1)
    handler(root, cfg)


def _ticket_spec_from_cfg(cfg: AppConfig, *, title: str, kind: str):  # noqa: ANN201
    """Build the `TicketSpec` `frob ticket new`'s flags describe.

    `title`/`kind` are taken as separate required params (not read again from
    `cfg.ticket_title`/`cfg.ticket_kind`) so the caller's None-check narrows
    them to `str` here too -- `cfg`'s fields stay `str | None` on their own.
    """
    from frob.tickets import Origin, Stride, TicketKind, TicketSpec

    return TicketSpec(
        title=title,
        kind=TicketKind(kind),
        origin=Origin(cfg.ticket_origin) if cfg.ticket_origin else Origin.HUMAN,
        scope=tuple(cfg.ticket_scope),
        blocked_by=tuple(cfg.ticket_blocked_by),
        parent=cfg.ticket_parent,
        acceptance=tuple(cfg.ticket_acceptance),
        threat=Stride(cfg.ticket_threat) if cfg.ticket_threat else None,
        body=cfg.ticket_body,
    )


def _maybe_attach_clipboard_image(root: Path, ticket_id: str) -> None:
    """Interactively (TTY only) offer to attach a clipboard image to `ticket_id`."""
    if not sys.stdin.isatty():
        return
    from frob.tickets import AttachmentSource, attach
    from frob.tickets.clipboard import clipboard_has_image

    if not clipboard_has_image():
        return
    answer = input(f"Attach clipboard image to {ticket_id}? [y/N] ").strip().lower()
    if answer != "y":
        return
    attach_result = attach(root, ticket_id, AttachmentSource(path=None), caption="")
    if attach_result.is_err:
        _log.error("clipboard attach failed: %s", attach_result.danger_err)
    else:
        _log.info("attached clipboard image to %s", ticket_id)


# frob:ticket T-0030
# frob:ticket T-0106
def _new(root: Path, cfg: AppConfig) -> None:
    """Create a ticket from `cfg`'s new-ticket flags; if `--evidence` ids
    were given, apply them (via `_apply_evidence`) after creation succeeds,
    then offer to attach a clipboard image on a TTY."""
    # frob:ticket T-0005
    from frob.tickets import new_ticket

    if cfg.ticket_title is None or cfg.ticket_kind is None:
        _log.error("frob ticket new requires --title and --kind")
        sys.exit(1)

    spec = _ticket_spec_from_cfg(cfg, title=cfg.ticket_title, kind=cfg.ticket_kind)
    result = new_ticket(root, spec)
    if result.is_err:
        _log.error("ticket new failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("created %s: %s", ticket.id, ticket.title)

    if cfg.ticket_evidence_ids:
        added = _apply_evidence(root, ticket.id, cfg.ticket_evidence_ids)
        if added.is_err:
            sys.exit(1)

    _maybe_attach_clipboard_image(root, ticket.id)


def _filter_by_state(tickets, state):
    """Tickets whose state equals `state` (extracted so `_list` stays a flat
    sequence of independent steps, not a nested-loop join)."""
    return [t for t in tickets if t.state == state]


def _list(root: Path, cfg: AppConfig) -> None:
    # Active store only (T-0096) -- archived done/dropped tickets would
    # otherwise pile back up in every `list` the archive command exists to
    # keep them out of.
    from frob.tickets import TicketState, load_active

    result = load_active(root)
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
    color = _stdout_color()
    for t in tickets:
        _log.info(
            "%s  [%s]  %s  (%s)",
            style_ticket_id(t.id, color),
            style_state(t.state.value, color),
            t.title,
            t.kind.value,
        )


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

    color = _stdout_color()
    _log.info(
        "%s  [%s]  %s  (%s)\nblocked_by=%s scope=%s\n\n%s",
        style_ticket_id(ticket.id, color),
        style_state(ticket.state.value, color),
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
    color = _stdout_color()
    for t in tickets:
        _log.info("%s  %s  (%s)", style_ticket_id(t.id, color), t.title, t.kind.value)


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


# frob:ticket T-0162
def _renumber(root: Path, cfg: AppConfig) -> None:
    """`frob ticket renumber <old> <new> [--dry-run]` rewrites one ticket's id
    everywhere (the first-class replacement for the old T-0157-incident sed);
    `frob ticket renumber` with no args keeps the legacy full-contiguous
    renumber (T-0012) for whole-ledger cleanup."""
    if cfg.ticket_old_id is not None or cfg.ticket_new_id is not None:
        _renumber_one(root, cfg)
        return
    if cfg.ticket_dry_run:
        _log.error(
            "frob ticket renumber --dry-run requires <old> <new> "
            "(no dry-run mode for the whole-ledger form)"
        )
        sys.exit(1)

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


def _renumber_one(root: Path, cfg: AppConfig) -> None:
    """`frob ticket renumber <old> <new>`: rewrite one ticket's id in the
    ledger(s) plus every frob: directive reference across the tracked tree."""
    from frob.tickets import renumber_one

    if cfg.ticket_old_id is None or cfg.ticket_new_id is None:
        _log.error("frob ticket renumber requires both <old> and <new>, or neither")
        sys.exit(1)

    result = renumber_one(
        root, cfg.ticket_old_id, cfg.ticket_new_id, dry_run=cfg.ticket_dry_run
    )
    if result.is_err:
        _log.error("ticket renumber failed: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok
    verb = "would rewrite" if report.dry_run else "rewrote"
    _log.info(
        "%s %s -> %s: ledger_changed=%s, %d code file(s) / %d reference(s)",
        verb,
        report.old_id,
        report.new_id,
        report.ledger_changed,
        len(report.files_changed),
        report.occurrences,
    )
    if report.files_changed:
        for f in report.files_changed:
            _log.info("  %s", f)


# frob:ticket T-0176
def _require_land_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket land`'s required
    `<id>`/`--worktree <path>` args are both present."""
    if cfg.ticket_id is None:
        _log.error("frob ticket land requires <id>")
        sys.exit(1)
    if cfg.ticket_worktree is None:
        _log.error("frob ticket land requires --worktree <path>")
        sys.exit(1)


def _report_land_result(root: Path, report) -> None:  # noqa: ANN001
    """Log every field of a `LandReport`: the dry-run summary line, or the
    landed commit plus each changed file."""
    if report.dry_run:
        _log.info(
            "land %s: DRY RUN clean -- merged=%s wip_committed=%s "
            "(would finalize/close/squash-apply/commit onto %s)",
            report.ticket_id,
            report.merged_main_into_worktree,
            report.wip_committed,
            root,
        )
        return
    _log.info(
        "land %s: landed as %s at %s (%d file(s) changed)",
        report.ticket_id,
        report.final_id,
        report.commit_sha,
        len(report.files_changed),
    )
    for f in report.files_changed:
        _log.info("  %s", f)


def _land(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land <id> --worktree <path> [--dry-run]`: run the whole
    merge-check-splice-close-commit chain via `frob.tickets.land`, reporting
    every field of the resulting `LandReport` (or the exact `Err` + remedy
    already logged by `land` itself) before exiting non-zero on failure."""
    from frob.tickets import land

    _require_land_args(cfg)
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced above
    assert cfg.ticket_worktree is not None

    result = land(root, cfg.ticket_id, cfg.ticket_worktree, dry_run=cfg.ticket_dry_run)
    if result.is_err:
        _log.error("ticket land failed: %s", result.danger_err)
        sys.exit(1)

    _report_land_result(root, result.danger_ok)


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


def _load_ticket_or_exit(root: Path, ticket_id: str, *, verb: str):  # noqa: ANN201
    """The ticket `ticket_id`, or exit(1) if the queue or lookup fails."""
    from frob.tickets import load_queue

    queue_result = load_queue(root)
    if queue_result.is_err:
        _log.error("ticket %s failed: %s", verb, queue_result.danger_err)
        sys.exit(1)
    ticket = queue_result.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        _log.error("no ticket %s", ticket_id)
        sys.exit(1)
    return ticket


def _auto_plan_if_queued(root: Path, ticket_id: str, ticket):  # noqa: ANN201
    """Transition a QUEUED ticket to PLANNED first; `start` takes both legal steps."""
    from frob.tickets import TicketState, transition

    if ticket.state != TicketState.QUEUED:
        return ticket
    planned = transition(root, ticket_id, TicketState.PLANNED)
    if planned.is_err:
        _log.error("ticket start failed: %s", planned.danger_err)
        sys.exit(1)
    _log.info("auto-planned %s (queued -> planned)", ticket_id)
    return planned.danger_ok


def _start(root: Path, cfg: AppConfig) -> None:
    """Transition to in-progress (auto-planning a queued ticket first) and
    run the pre-work sweep. Starting a ticket that is ALREADY in-progress is
    a hard error, not a silent no-op or refresh (T-0215): `frob ticket
    sweep <id>` already exists as the idempotent refresh path, so re-running
    `start` on an in-progress ticket is treated as a coordinator mistake and
    named explicitly, pointing at `sweep` instead of quietly duplicating it."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket start requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="start")
    if ticket.state == TicketState.IN_PROGRESS:
        _log.error(
            "ticket start failed: %s is already in-progress -- run "
            "`frob ticket sweep %s` to refresh the pre-work sweep instead",
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    ticket = _auto_plan_if_queued(root, cfg.ticket_id, ticket)

    transitioned = transition(root, cfg.ticket_id, TicketState.IN_PROGRESS)
    if transitioned.is_err:
        _log.error("ticket start failed: %s", transitioned.danger_err)
        sys.exit(1)

    _run_sweep(root, transitioned.danger_ok)


def _sweep_cmd(root: Path, cfg: AppConfig) -> None:
    """Re-record the pre-work sweep for an in-progress ticket (scope widened)."""
    from frob.tickets import TicketState

    if cfg.ticket_id is None:
        _log.error("frob ticket sweep requires <id>")
        sys.exit(1)
    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="sweep")
    if ticket.state != TicketState.IN_PROGRESS:
        _log.error("ticket sweep: %s is not in-progress", cfg.ticket_id)
        sys.exit(1)
    _run_sweep(root, ticket)


def _xref_hits_for_scope(root: Path, scope: tuple[str, ...]) -> list[str]:
    """Symbol names `xref` resolves for each scope glob's basename stem."""
    from frob.xref import xref

    xref_hits: list[str] = []
    for pattern in scope:
        base = pattern.split("*", 1)[0].rstrip("/") or "."
        scan_path = root / base if base != "." else root
        if not scan_path.exists():
            continue
        symbol = Path(pattern).stem
        xref_result = xref(symbol, root)
        if xref_result.is_ok:
            xref_hits.append(xref_result.danger_ok.symbol)
    return xref_hits


def _scope_digest_for_ticket(root: Path, ticket) -> str:  # noqa: ANN001
    """`scope_digest` for `ticket`, loading (or building) the graph cache first.

    MUST come from frob.gates.scope_digest -- the gate compares against the
    same function, so recording and checking can never desync.
    """
    from frob.gates import scope_digest
    from frob.graph import build_graph, load_graph

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        loaded = build_graph(root, cache)
    return scope_digest(ticket.scope, loaded.danger_ok) if loaded.is_ok else ""


def _run_sweep(root: Path, ticket) -> None:
    """Record the pre-work sweep (dup + xref + scope digest) for `ticket`."""
    from frob.dup import find_duplicates
    from frob.gates import PreworkSweep, record_prework

    dup_result = find_duplicates(root)
    dup_findings = dup_result.total_clones
    xref_hits = _xref_hits_for_scope(root, ticket.scope or (".",))
    digest = _scope_digest_for_ticket(root, ticket)

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

    # No path means "read from clipboard" -- but a non-interactive agent
    # session has no clipboard to paste from, and would otherwise hang or
    # spawn a clipboard backend that can never produce an image (T-0098).
    if cfg.ticket_attach_path is None and not sys.stdin.isatty():
        _log.error(
            "frob ticket attach %s: no path given and stdin is not a TTY "
            "(non-interactive session cannot paste from the clipboard); "
            "pass an explicit file path: frob ticket attach %s <path>",
            cfg.ticket_id,
            cfg.ticket_id,
        )
        sys.exit(1)

    source = AttachmentSource(path=cfg.ticket_attach_path)
    result = attach(root, cfg.ticket_id, source, caption=cfg.ticket_caption)
    if result.is_err:
        _log.error("attach failed: %s", result.danger_err)
        sys.exit(1)
    attachment = result.danger_ok
    _log.info("attached %s (sha256=%s)", attachment.path, attachment.sha256)


# frob:ticket T-0081
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
    # frob:channel f_cli_tickets
    # design/frob.strata's `flow f_cli_tickets : cli -> tickets_ledger` --
    # this is one of the cli-layer write sites into the ticket ledger.
    written = write_ticket(root, updated)
    if written.is_err:
        _log.error("block failed: %s", written.danger_err)
        sys.exit(1)
    _log.info("%s now blocked by %s", cfg.ticket_id, cfg.ticket_by)


# frob:ticket T-0215
def _close_failure_hint(ticket_id: str, state, err) -> str:  # noqa: ANN001
    """The log message for a failed close: names a concrete remedy instead of
    just echoing the raw error (T-0215 -- both close-on-queued's
    InvalidTransition and MissingEvidence used to log with no next step)."""
    from frob.tickets import TicketError, TicketState

    if err == TicketError.InvalidTransition and state in (
        TicketState.QUEUED,
        TicketState.PLANNED,
    ):
        return (
            f"close failed: {err} -- {ticket_id} is {state.value}, not "
            f"in-progress -- run `frob ticket start {ticket_id}` first"
        )
    if err == TicketError.MissingEvidence:
        return (
            f"close failed: {err} -- {ticket_id} is missing evidence or a "
            f"Done report -- add evidence (`frob ticket evidence {ticket_id} "
            f"<node-id>...`, or for a docs-kind ticket `--evidence-cmd "
            f"'<command>'`) and write a '## Done report' heading under "
            f"{ticket_id}'s section in tickets.md"
        )
    return f"close failed: {err}"


# frob:ticket T-0106
# frob:ticket T-0215
def _close(root: Path, cfg: AppConfig) -> None:
    """Transition a ticket to done; if `--evidence` ids or `--evidence-cmd`
    were given, validate and append them first (`_apply_evidence` /
    `_apply_cmd_evidence`) and refuse to transition at all if either is
    unresolvable/fails, so a bad flag can never close a ticket on
    unvalidated evidence. A failed transition is reported through
    `_close_failure_hint` so the operator gets a concrete next command, not
    just the bare state-machine error (T-0215)."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket close requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")

    if cfg.ticket_evidence_ids:
        added = _apply_evidence(root, cfg.ticket_id, cfg.ticket_evidence_ids)
        if added.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_added = _apply_cmd_evidence(root, cfg.ticket_id, cfg.ticket_evidence_cmd)
        if cmd_added.is_err:
            sys.exit(1)

    result = transition(root, cfg.ticket_id, TicketState.DONE)
    if result.is_err:
        _log.error(_close_failure_hint(cfg.ticket_id, ticket.state, result.danger_err))
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


# frob:ticket T-0094
# frob:ticket T-0106
# frob:ticket T-0215
def _evidence(root: Path, cfg: AppConfig) -> None:
    """Validate `cfg.ticket_evidence_ids` against collected pytest node ids
    and append the resolvable ones to the ticket's structured evidence list;
    or, with `--evidence-cmd`, record the T-0215 non-pytest cmd-evidence
    entry instead (docs-kind tickets only). Requires at least one of the
    two -- neither is silently a no-op."""
    has_evidence = cfg.ticket_evidence_ids or cfg.ticket_evidence_cmd
    if cfg.ticket_id is None or not has_evidence:
        _log.error(
            "frob ticket evidence requires <id> and either <pytest-node-id>... "
            "or --evidence-cmd 'command'"
        )
        sys.exit(1)

    if cfg.ticket_evidence_ids:
        result = _apply_evidence(root, cfg.ticket_id, cfg.ticket_evidence_ids)
        if result.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_result = _apply_cmd_evidence(root, cfg.ticket_id, cfg.ticket_evidence_cmd)
        if cmd_result.is_err:
            sys.exit(1)


# frob:ticket T-0106
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_evidence(root: Path, ticket_id: str, node_ids: list[str]):
    """Collect pytest node ids, validate `node_ids` against them via
    `frob.tickets.add_evidence` (resolvable-id + dedupe semantics, wholesale
    batch rejection on any unresolvable id), and append the resolvable ones
    to `ticket_id`'s structured evidence list. Shared by `frob ticket
    evidence`, `frob ticket new --evidence`, and `frob ticket close
    --evidence` so all three routes go through identical validation --
    never through an ad hoc, unvalidated write. Returns the `add_evidence`
    Result unchanged so callers (e.g. `_close`) can refuse to transition
    state on failure.

    T-0301 (feldspar T-0015 escalation): a `--evidence` id must resolve
    against the union of every collected oracle the repo's `[[test.runner]]`
    entries declare, not pytest alone -- a rust node id IS collected (via
    `collect_rust_tests`, into `.frob/cargo-collect.json`) whenever
    `frob.toml` declares a `language = "rust"` runner, so it must be part of
    the same oracle set pytest ids validate against. Rust collection is
    attempted only when a rust runner is actually configured (repos with no
    rust runner never pay a `cargo` invocation here), and a rust-collection
    failure degrades to a WARNING plus python-only validation rather than
    blocking evidence recording outright -- an unrelated cargo/pyo3
    environment problem must not stop a purely-python ticket's evidence
    from being recorded (same resilience posture as T-0144's `make core`
    guidance elsewhere in this module)."""
    from frob.testing import collect_python_tests, collect_rust_tests, load_runners
    from frob.tickets import add_evidence

    collected = collect_python_tests(root)
    if collected.is_err:
        _log.error(
            "ticket evidence: pytest collection failed: %s", collected.danger_err
        )
        return collected

    collected_ids = set(collected.danger_ok.node_ids)

    runners = load_runners(root)
    if runners.is_ok and any(spec.language == "rust" for spec in runners.danger_ok):
        rust_collected = collect_rust_tests(root)
        if rust_collected.is_err:
            _log.warning(
                "ticket evidence: rust collection failed (%s); validating "
                "against pytest ids only for this call",
                rust_collected.danger_err,
            )
        else:
            collected_ids |= rust_collected.danger_ok.node_ids

    result = add_evidence(root, ticket_id, node_ids, frozenset(collected_ids))
    _log_evidence_result(ticket_id, result)
    return result


def _log_evidence_result(ticket_id: str, result) -> None:  # noqa: ANN001
    """Log `add_evidence`'s outcome: the failure reason + remedy, or the
    ticket's resulting evidence id count."""
    if result.is_err:
        _log.error(
            "ticket evidence failed: %s (run `frob test --collect` to refresh "
            "collected tests, or fix the id)",
            result.danger_err,
        )
        return

    ticket = result.danger_ok
    _log.info(
        "%s: evidence now has %d id(s): %s",
        ticket_id,
        len(ticket.evidence),
        list(ticket.evidence),
    )


# frob:ticket T-0215
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_cmd_evidence(root: Path, ticket_id: str, command: str):
    """Run `command` via `frob.tickets.add_cmd_evidence` and append its
    exit-status/digest entry to `ticket_id`'s evidence list -- the
    docs/design-kind non-pytest evidence channel (T-0215). Returns the
    `add_cmd_evidence` Result unchanged so callers (`_close`, `_evidence`)
    can refuse to transition state on failure, the same contract
    `_apply_evidence` gives pytest-node-id evidence."""
    from frob.tickets import add_cmd_evidence

    result = add_cmd_evidence(root, ticket_id, command)
    if result.is_err:
        _log.error(
            "ticket evidence-cmd failed: %s (docs-kind tickets only; code "
            "kinds require pytest --evidence node ids)",
            result.danger_err,
        )
        return result

    ticket = result.danger_ok
    _log.info(
        "%s: evidence now has %d entries: %s",
        ticket_id,
        len(ticket.evidence),
        list(ticket.evidence),
    )
    return result


# frob:ticket T-0096
def _archive(root: Path) -> None:
    """Move every done/dropped ticket from the active ledger into
    tickets-archive.md, verbatim (idempotent -- a second run finds nothing
    to move)."""
    from frob.tickets import archive

    result = archive(root)
    if result.is_err:
        _log.error("ticket archive failed: %s", result.danger_err)
        sys.exit(1)
    n = result.danger_ok
    if n == 0:
        _log.info("nothing to archive")
    else:
        _log.info("archived %d ticket(s) into tickets-archive.md", n)
