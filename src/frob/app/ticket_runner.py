"""CLI wiring for `frob ticket new|list|show|doable|board|epic|brief|plan|
start|requeue|sweep|reconcile|land|merge-driver|attach|block|close|fail|
drop|evidence|done-report|scope|priority|kind|component|label|archive|
review` (docs/modules/tickets.md)."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/app/ticket_runner.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

# frob:waive TEST005 reason="module line coverage 22.7%, debt T-0160"
# frob:waive SCOPE001 reason="T-0323 scope omitted this file, filed T-draft-bc39c17f"
# frob:waive SCOPE001 reason="T-0453 needs doable --show-blocked/--ignore-lease wiring here, T-0176/T-0220 precedent"  # noqa: E501
# frob:waive SCOPE001 reason="T-0411 needs new --priority/priority-subcommand wiring here; T-0453/T-0455 bootstrap precedent, T-0446 tracks the general gap"  # noqa: E501

from __future__ import annotations

import re
import subprocess
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

from typani.result import Err, Ok

from frob.app._style import style_state, style_ticket_id
from frob.app.config import AppConfig
from frob.logging import get_logger, logger_levels
from frob.process._guard import (
    EXEC_KILL_SWITCH_ENV,
    ProcessGuardError,
    exec_enabled,
    guarded_subprocess_run,
)

if TYPE_CHECKING:
    from frob.tickets import TicketQueue

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
        "requeue": _requeue,
        "sweep": _sweep_cmd,
        "reconcile": _reconcile_cmd,
        "migrate": lambda root, _cfg: _migrate(root),
        "renumber": _renumber,
        "land": _land,
        "merge-driver": _merge_driver,
        "attach": _attach,
        "block": _block,
        "close": _close,
        "fail": _fail,
        "drop": _drop,
        "evidence": _evidence,
        "done-report": _done_report,
        "review": _review,
        "scope": _scope,
        "priority": _priority,
        "kind": _kind,
        "component": _component,
        "label": _label,
        "board": _board,
        "epic": _epic,
        "brief": _brief,
        "archive": lambda root, cfg: _archive(root, force=cfg.ticket_force),
    }


# frob:doc docs/modules/app.md#runners
# frob:waive TEST005 reason="run 20.0% branch cover, debt T-0160"
def run(cfg: AppConfig) -> None:
    """Dispatch to the ticket subcommand named by `cfg.ticket_command`."""
    root = (cfg.ticket_path or Path(".")).resolve()

    handler = _ticket_dispatch_table().get(cfg.ticket_command)
    if handler is None:
        _log.error(
            "usage: frob ticket <new|list|show|doable|board|epic|brief|plan|"
            "start|requeue|sweep|reconcile|land|merge-driver|attach|block|"
            "close|fail|drop|evidence|done-report|scope|priority|kind|"
            "component|label|archive|review> ..."
        )
        sys.exit(1)
    with _diagnostic_log_ctx(cfg):
        handler(root, cfg)


# frob:ticket T-0768
def _diagnostic_log_ctx(cfg: AppConfig):  # noqa: ANN202
    """The logger context `run` dispatches every subcommand under (T-0768).

    At default verbosity the `frob` logger tree is clamped to WARNING so
    library diagnostic chatter (`frob.gitio` spawn/returncode lines, the
    `frob.tickets` loader's per-run INFO) stays out of the terminal, while
    this module's own logger -- the ticket CLI's user-facing output channel
    -- is pinned to INFO so listings still print. `-v` skips the clamp and
    restores the full firehose. WARNING+ lines (stale leases, over-broad
    scopes) always show either way.
    """
    import contextlib
    import logging

    if cfg.ticket_verbose > 0:
        return contextlib.nullcontext()
    return logger_levels({"frob": logging.WARNING, __name__: logging.INFO})


# frob:ticket T-0737
def _resolve_new_body(cfg: AppConfig) -> str:
    """Resolve `frob ticket new`'s body: `--body-file` wins if given (read
    verbatim, byte-for-byte -- T-0737, so backticked/quoted/`$`-laden prose
    never rides the shell), else the inline `--body` string. Exits 1 if
    both are given (ambiguous which the caller meant) or the file cannot be
    read."""
    if cfg.ticket_body_file is not None and cfg.ticket_body:
        _log.error("frob ticket new: --body and --body-file are mutually exclusive")
        sys.exit(1)
    if cfg.ticket_body_file is not None:
        try:
            return cfg.ticket_body_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket new: could not read --body-file %s: %s",
                cfg.ticket_body_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_body


# frob:ticket T-0737
def _parse_acceptance_file(text: str) -> list[str]:
    """Split `--acceptance-file` contents into criteria: one criterion per
    blank-line-separated block (T-0737) -- chosen over strict one-per-line
    so a multi-sentence GIVEN/WHEN/THEN criterion may still wrap across
    lines within its own block. A file with no blank lines degrades
    gracefully to one criterion per non-empty line. Blocks are stripped of
    leading/trailing whitespace; empty blocks are dropped."""
    if re.search(r"\n\s*\n", text):
        blocks = [b.strip() for b in re.split(r"\n\s*\n+", text)]
        return [b for b in blocks if b]
    return [line.strip() for line in text.splitlines() if line.strip()]


# frob:ticket T-0737
def _resolve_new_acceptance(cfg: AppConfig) -> list[str]:
    """Resolve `frob ticket new`'s acceptance criteria: `--acceptance-file`
    wins if given (parsed via `_parse_acceptance_file`, T-0737), else the
    repeated `--acceptance TEXT` flags. Exits 1 if both are given (ambiguous
    which the caller meant) or the file cannot be read."""
    if cfg.ticket_acceptance_file is not None and cfg.ticket_acceptance:
        _log.error(
            "frob ticket new: --acceptance and --acceptance-file are mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_acceptance_file is not None:
        try:
            text = cfg.ticket_acceptance_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket new: could not read --acceptance-file %s: %s",
                cfg.ticket_acceptance_file,
                exc,
            )
            sys.exit(1)
        return _parse_acceptance_file(text)
    return list(cfg.ticket_acceptance)


def _ticket_spec_from_cfg(cfg: AppConfig, *, title: str, kind: str):  # noqa: ANN201
    """Build the `TicketSpec` `frob ticket new`'s flags describe.

    `title`/`kind` are taken as separate required params (not read again from
    `cfg.ticket_title`/`cfg.ticket_kind`) so the caller's None-check narrows
    them to `str` here too -- `cfg`'s fields stay `str | None` on their own.
    """
    from frob.tickets import Origin, Priority, Stride, TicketKind, TicketSpec

    return TicketSpec(
        title=title,
        kind=TicketKind(kind),
        origin=Origin(cfg.ticket_origin) if cfg.ticket_origin else Origin.HUMAN,
        # frob:ticket T-0411
        priority=(
            Priority(cfg.ticket_priority) if cfg.ticket_priority else Priority.MEDIUM
        ),
        scope=tuple(cfg.ticket_scope),
        blocked_by=tuple(cfg.ticket_blocked_by),
        parent=cfg.ticket_parent,
        # T-0572: `--acceptance TEXT` (repeatable) gives plain strings;
        # TicketSpec's `_coerce_acceptance_field` validator wraps each into
        # a fresh, unbound {text, evidence: ()} AcceptanceCriterion --
        # `type: ignore` names the mismatch this validator exists to close
        # (the annotated field type is the POST-validation shape).
        # frob:ticket T-0737
        # `_resolve_new_acceptance` picks --acceptance or --acceptance-file.
        acceptance=tuple(  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
            _resolve_new_acceptance(cfg)
        ),
        threat=Stride(cfg.ticket_threat) if cfg.ticket_threat else None,
        # frob:ticket T-0454
        component=cfg.ticket_component,
        labels=tuple(cfg.ticket_labels),
        # frob:ticket T-0737
        # `_resolve_new_body` picks --body or --body-file.
        body=_resolve_new_body(cfg),
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
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=ticket.id, event="created")

    if cfg.ticket_evidence_ids:
        added = _apply_evidence(root, ticket.id, cfg.ticket_evidence_ids)
        if added.is_err:
            sys.exit(1)

    _maybe_attach_clipboard_image(root, ticket.id)


def _filter_by_state(tickets, state):
    """Tickets whose state equals `state` (extracted so `_list` stays a flat
    sequence of independent steps, not a nested-loop join)."""
    return [t for t in tickets if t.state == state]


# frob:ticket T-0716
def _list(root: Path, cfg: AppConfig) -> None:
    # Active store only (T-0096) -- archived done/dropped tickets would
    # otherwise pile back up in every `list` the archive command exists to
    # keep them out of.
    from frob.tickets import TicketState, display_state, load_active

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
            style_state(display_state(t, root), color),
            t.title,
            t.kind.value,
        )


# frob:ticket T-0716
def _show(root: Path, cfg: AppConfig) -> None:
    from frob.tickets import display_state, load_queue

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
        "%s  [%s]  %s  (%s)\nblocked_by=%s scope=%s%s\n\n%s",
        style_ticket_id(ticket.id, color),
        style_state(display_state(ticket, root), color),
        ticket.title,
        ticket.kind.value,
        list(ticket.blocked_by),
        list(ticket.scope),
        _render_acceptance(ticket),
        ticket.body,
    )


# frob:ticket T-0572
def _render_acceptance(ticket) -> str:  # noqa: ANN001
    """The `\\nacceptance[i]: <bound|UNBOUND> <text>` lines `frob ticket
    show` appends after `scope=` (T-0572) -- the human-readable surface for
    finding an acceptance item's 0-based index to bind with `frob ticket
    evidence <id> <node-id> --accepts <index>`, without needing `--json`.
    Empty string (no extra lines) when the ticket declares no acceptance
    criteria at all, matching pre-T-0572 output exactly."""
    if not ticket.acceptance:
        return ""
    lines = ["\nacceptance:"]
    for i, item in enumerate(ticket.acceptance):
        status = f"bound({list(item.evidence)})" if item.evidence else "UNBOUND"
        lines.append(f"  [{i}] {status}: {item.text}")
    return "\n".join(lines)


# frob:ticket T-0453
def _doable(root: Path, cfg: AppConfig) -> None:
    """Render `frob ticket doable`: the default collision-safe list, or
    `--show-blocked`'s per-exclusion explanation, or `--ignore-lease`'s raw
    blocker-only list (T-0453 scope-lease model) -- also always prints an
    "Active leases" section (what's holding the tree) and large-glob-
    warning nudges, and a clear message when the result is empty.

    T-0752: the default (non-json) render additionally (1) shows each
    row's priority, (2) splits rows with a live lease against them
    (`has_live_lease`, T-0716 overlay) into a separate IN-FLIGHT section
    below the truly-dispatchable ones, and (3) marks any CRITICAL/HIGH row
    that has sat dispatchable past its staleness threshold
    (`undispatched_stale`) with a loud UNDISPATCHED alarm, sorted to the
    top of the dispatchable section. `--json`/`--ignore-lease` keep the
    prior raw/undecorated shape -- the split and alarm are a display-layer
    concern for the human-facing listing only, not a change to what
    `doable()` itself returns."""
    from frob.tickets import (
        doable,
        has_live_lease,
        load_queue,
        scope_breadth_context,
        undispatched_stale,
    )

    result = load_queue(root)
    if result.is_err:
        _log.error("ticket doable failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    # T-0453 perf fix: computed ONCE per invocation and threaded through
    # every lease/warning check below -- never re-walked per candidate.
    breadth = scope_breadth_context(root)

    if cfg.ticket_show_blocked:
        _render_doable_show_blocked(root, queue, cfg, breadth=breadth)
        return

    # T-0752: thread the ALREADY-COMPUTED `breadth` through so `doable()`
    # does not re-walk the tree a second time for it -- `doable_blocked`
    # already took this kwarg; `doable` gained it for exactly this call
    # (was the spawn-budget regression: a second `git ls-files` per
    # invocation before this fix).
    tickets = doable(queue, root, ignore_lease=cfg.ticket_ignore_lease, breadth=breadth)

    if cfg.ticket_json:
        import json

        _log.info(json.dumps([t.model_dump(mode="json") for t in tickets], indent=2))
        return

    _render_active_leases(queue)

    for warning in _active_large_glob_warnings(root, queue, breadth=breadth):
        _log.warning("ticket doable: %s", warning)

    if not tickets:
        _log.info(
            "zero doable tickets (no available lease found in repo tree; "
            "starting any ticket would conflict with a ticket in progress)"
        )
        return

    # T-0752 dispatch-state split: a row `doable()` returned may still have
    # a live lease of its OWN (a worktree started it before main's ledger
    # learned about it, T-0716's @worktree case) -- those belong in-flight,
    # not in the "next thing to dispatch" section.
    in_flight = [t for t in tickets if has_live_lease(t, root)]
    dispatchable = [t for t in tickets if t not in in_flight]

    alarms = undispatched_stale(dispatchable, root)
    alarmed_ids = {t.id for t, _elapsed, _threshold in alarms}
    ordered = [t for t in dispatchable if t.id in alarmed_ids] + [
        t for t in dispatchable if t.id not in alarmed_ids
    ]
    alarm_by_id = {t.id: (elapsed, threshold) for t, elapsed, threshold in alarms}

    color = _stdout_color()
    for t in ordered:
        row = "%s  %s  (%s)  priority=%s" % (
            style_ticket_id(t.id, color),
            t.title,
            t.kind.value,
            t.priority.value,
        )
        if t.id in alarm_by_id:
            elapsed, threshold = alarm_by_id[t.id]
            row += "  [UNDISPATCHED %.0fh > %.0fh threshold]" % (elapsed, threshold)
        _log.info(row)

    if in_flight:
        _log.info("In-flight (leased, already being worked):")
        for t in in_flight:
            _log.info(
                "  %s  %s  (%s)  priority=%s",
                style_ticket_id(t.id, color),
                t.title,
                t.kind.value,
                t.priority.value,
            )


# frob:ticket T-0453
def _render_active_leases(queue: "TicketQueue") -> None:
    """Print a compact "Active leases" line per IN-PROGRESS ticket (id,
    title, scope) so the user always sees what's currently holding the
    tree, ahead of the doable list itself (T-0453 UX request)."""
    from frob.tickets import TicketState

    holders = sorted(
        (t for t in queue.tickets.values() if t.state is TicketState.IN_PROGRESS),
        key=lambda t: t.id,
    )
    if not holders:
        _log.info("Active leases: none")
        return
    color = _stdout_color()
    _log.info("Active leases:")
    for t in holders:
        _log.info(
            "  %s  %s  scope=%s", style_ticket_id(t.id, color), t.title, list(t.scope)
        )


# frob:ticket T-0453
def _active_large_glob_warnings(
    root: Path,
    queue: "TicketQueue",
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> list[str]:
    """Large-glob-warning nudges (T-0453) for every ticket currently
    holding a scope-lease (in-progress) or waiting to (queued/planned) --
    surfaced alongside `frob ticket doable` output so an over-broad scope
    that is serializing the queue is visible, not silently hand-diagnosed.
    Pass a precomputed `breadth` (`scope_breadth_context(root)`) so the
    breadth walk runs once for the whole listing, not once per ticket."""
    from frob.tickets import TicketState, large_glob_warnings

    warnings: list[str] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state in (
            TicketState.IN_PROGRESS,
            TicketState.QUEUED,
            TicketState.PLANNED,
        ):
            warnings.extend(large_glob_warnings(t, root, breadth=breadth))
    return warnings


# frob:ticket T-0453
def _render_doable_show_blocked(
    root: Path,
    queue: "TicketQueue",
    cfg: AppConfig,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> None:
    """Render `frob ticket doable --show-blocked`: every doable-candidate
    currently hidden by an in-progress scope-lease, with the holding
    ticket id and the overlapping glob named (T-0453)."""
    from frob.tickets import doable_blocked

    blocked = doable_blocked(queue, root, breadth=breadth)

    if cfg.ticket_json:
        import json

        payload = [
            {
                "ticket": t.model_dump(mode="json"),
                "held_by": [
                    {"ticket_id": holder_id, "glob": glob} for holder_id, glob in hits
                ],
            }
            for t, hits in blocked
        ]
        _log.info(json.dumps(payload, indent=2))
        return

    if not blocked:
        _log.info("nothing held back by a scope-lease")
        return
    color = _stdout_color()
    for t, hits in blocked:
        reasons = "; ".join(
            f"scope {glob!r} leased by in-progress {holder_id}"
            for holder_id, glob in hits
        )
        _log.info("%s  %s  held: %s", style_ticket_id(t.id, color), t.title, reasons)


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
    if report.release_bumped_to is not None:
        _log.info(
            "land %s: REL001 bumped to %s",
            report.ticket_id,
            report.release_bumped_to,
        )
    if report.natives_rebuilt:
        _log.info("land %s: native extension(s) rebuilt", report.ticket_id)


# frob:ticket T-0398
def _land_collected_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with no args, AFTER its
    internal merge, to get the post-merge worktree's collected node ids.
    Best-effort -- a collection failure logs and returns an empty set
    (fail-closed: `land`'s post-merge check then treats every non-cmd
    evidence id as unresolved, refusing the landing, rather than silently
    skipping the check)."""

    def fn() -> frozenset[str]:
        collected = _collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as unresolved",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, _runners = collected.danger_ok
        return python_ids | rust_ids

    return fn


# frob:ticket T-0398
def _land_passed_fn(worktree: Path):  # noqa: ANN201
    """D-05 CLI closure: `land()` calls this with the post-merge ticket's
    non-cmd evidence ids, AFTER its internal merge, and expects back the
    subset actually observed passing -- reuses `_verify_ids_passing`
    (D-01's same real-run verification) against the worktree."""

    def fn(node_ids) -> frozenset[str]:  # noqa: ANN001
        collected = _collect_python_and_rust_ids(worktree)
        if collected.is_err:
            _log.warning(
                "land: post-merge collection failed (%s) -- treating all "
                "evidence as NOT passing",
                collected.danger_err,
            )
            return frozenset()
        python_ids, rust_ids, runners = collected.danger_ok
        return _verify_ids_passing(worktree, node_ids, python_ids, rust_ids, runners)

    return fn


# frob:ticket T-0398
# frob:ticket T-0774
def _land_covers_scope_fn(worktree: Path):  # noqa: ANN201
    """D-05/D-02 CLI closure: `land()` calls this TWICE -- once (T-0774) as
    a PRE-merge preflight simulation with the worktree's still-unmerged
    `Ticket` (via `_land_precheck`), and once, as before, with the post-
    merge/post-finalize `Ticket` (via `_land_finalize_and_close`) -- and
    expects back the D-02 scope-binding answer computed against the
    WORKTREE's graph (not root's) either way. `worktree` itself does not
    change between the two calls (it is this same closure's captured
    argument); only the ticket state on disk under it does, since `land`'s
    internal merge mutates the worktree tree in between. The post-merge
    call remains authoritative -- the merged, about-to-be-squashed tree is
    the one whose scope/evidence actually matter -- the pre-merge call is
    only an early, best-effort refusal for the common case where the
    ticket's scope files are untouched by any concurrent main-side change."""

    def fn(ticket):  # noqa: ANN001, ANN202
        return _covers_scope_for_ticket(worktree, ticket)

    return fn


# frob:ticket T-0338
def _land_bump_version_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this AFTER the squash-apply is staged
    onto `root`, computing whatever `frob.release` says the just-squashed
    public API demands and applying it -- the REL001 half of T-0338's
    coordinator-plumbing consolidation. `frob.release`/`frob.graph` access
    lives here (the CLI layer), not in `frob.tickets` (docs/rework.md
    cycle-avoidance, same reasoning as `_land_covers_scope_fn`)."""

    def fn(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN202
        return _apply_release_bump_for_land(root, ticket, final_id)

    return fn


# frob:ticket T-0338
def _required_release_bump(root: Path, final_id: str):  # noqa: ANN201
    """The REL001-required version string for `root`'s current public API
    against its tracked release manifest, or `Ok(None)` if no bump is
    needed (no manifest yet, or `BumpClass.NONE`) -- split out of
    `_apply_release_bump_for_land` to keep each half under the ARCH001
    line-count threshold (T-0338)."""
    from frob.release import BumpClass, diff_class, load_manifest, required_version
    from frob.tickets._land import LandError

    manifest_result = load_manifest(root)
    if manifest_result.is_err:
        _log.debug("land: no release manifest at %s, skipping REL001 bump", root)
        return Ok(None)
    manifest = manifest_result.danger_ok

    snapshot = _graph_snapshot(root)
    if snapshot.is_err:
        _log.error(
            "land: %s graph unavailable (%s), cannot compute REL001 bump",
            final_id,
            snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)

    bump = diff_class(manifest, snapshot.danger_ok)
    if bump == BumpClass.NONE:
        return Ok(None)

    needed = required_version(manifest.version, bump)
    if needed.is_err:
        _log.error(
            "land: %s manifest version %r is not parseable, cannot compute REL001 bump",
            final_id,
            manifest.version,
        )
        return Err(LandError.ReleaseBumpFailed)
    return Ok(needed.danger_ok)


# frob:ticket T-0338
def _apply_release_bump_for_land(root: Path, ticket, final_id: str):  # noqa: ANN001, ANN201
    """Compute the REL001 bump class for `root`'s just-squashed public API
    against its release manifest and, if the declared version does not
    already cover it, bump `pyproject.toml`'s `version`, append a minimal
    CHANGELOG.md entry (satisfies `_changelog_mentions`'s "the version
    string appears somewhere" contract), and `frob release stamp` the new
    manifest -- staging all three files in `root`'s index so they land in
    the same commit as the squash-apply (T-0338).

    Returns `Ok(None)` (no write at all) when no manifest exists yet (the
    repo has never opted into `frob release stamp`) or when the diff class
    is `BumpClass.NONE`; `Ok(new_version)` after a successful bump+stamp;
    `Err(LandError.ReleaseBumpFailed)` on any failure along the way (an
    unreadable manifest, an unparsable `pyproject.toml` version, or a
    graph build failure) -- fail-closed, since a silently-skipped bump
    would let a landed API change slip past REL001 undetected."""
    from frob.gitio import run_argv
    from frob.release import stamp
    from frob.tickets._land import LandError

    needed = _required_release_bump(root, final_id)
    if needed.is_err:
        return Err(needed.danger_err)
    if needed.danger_ok is None:
        return Ok(None)
    new_version = needed.danger_ok

    written = _write_release_bump(root, ticket, final_id, new_version)
    if written.is_err:
        return Err(written.danger_err)

    fresh_snapshot = _graph_snapshot(root)
    if fresh_snapshot.is_err:
        _log.error(
            "land: %s graph unavailable post-bump (%s), cannot stamp release manifest",
            final_id,
            fresh_snapshot.danger_err,
        )
        return Err(LandError.ReleaseBumpFailed)
    stamp(root, fresh_snapshot.danger_ok, new_version)

    staged = run_argv(
        [
            "git",
            "-C",
            str(root),
            "add",
            "pyproject.toml",
            "CHANGELOG.md",
            ".frob-release.json",
        ]
    )
    if staged.is_err or staged.danger_ok.returncode != 0:
        _log.error("land: %s failed to stage the REL001 bump files", final_id)
        return Err(LandError.ReleaseBumpFailed)
    return Ok(new_version)


# frob:ticket T-0338
_PYPROJECT_VERSION_RE = re.compile(r'(?m)^version\s*=\s*"[^"]*"')


def _write_release_bump(root: Path, ticket, final_id: str, new_version: str):  # noqa: ANN001, ANN201
    """Rewrite `root/pyproject.toml`'s `version = "..."` line to
    `new_version` and append a minimal `## [new_version] - unreleased`
    CHANGELOG.md entry naming `final_id`/`ticket.title` (T-0338)."""
    from frob.tickets._land import LandError

    pyproject_path = root / "pyproject.toml"
    text = pyproject_path.read_text(encoding="utf-8")
    new_text, count = _PYPROJECT_VERSION_RE.subn(
        f'version = "{new_version}"', text, count=1
    )
    if count != 1:
        _log.error(
            'land: %s could not find a `version = "..."` line in %s',
            final_id,
            pyproject_path,
        )
        return Err(LandError.ReleaseBumpFailed)
    pyproject_path.write_text(new_text, encoding="utf-8")

    changelog_path = root / "CHANGELOG.md"
    changelog_text = changelog_path.read_text(encoding="utf-8")
    entry = f"## [{new_version}] - unreleased\n\n- {final_id}: {ticket.title}\n\n"
    lines = changelog_text.splitlines(keepends=True)
    insert_at = next(
        (i for i, line in enumerate(lines) if line.startswith("## ")), len(lines)
    )
    lines[insert_at:insert_at] = [entry]
    changelog_path.write_text("".join(lines), encoding="utf-8")
    _log.info(
        "land: %s wrote REL001 bump -> %s in %s and %s",
        final_id,
        new_version,
        pyproject_path,
        changelog_path,
    )
    return Ok(None)


# frob:ticket T-0338
def _land_rebuild_natives_fn():  # noqa: ANN201
    """CLI closure: `land()` calls this with `root` only when the landed
    changeset touches a native source tree (frob-core/, strata-core/) --
    runs `make core` in `root` and returns whether it exited 0 (T-0338).
    Best-effort: `land` treats a `False` as a logged warning, never a hard
    failure (a native rebuild is cheap to re-run by hand, and a `make
    core` failure in a from-scratch clone is not necessarily this land's
    fault)."""

    def fn(root: Path) -> bool:
        # T-0803: routed through `guarded_subprocess_run` (T-0778's guard)
        # so `FROB_DISABLE_EXEC=1` refuses this `make core` spawn too;
        # treated as a failed rebuild (`False`, logged) rather than a hard
        # error, matching this function's existing best-effort contract.
        guarded = guarded_subprocess_run(
            ["make", "core"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if guarded.is_err:
            _log.warning(
                "land: `make core` in %s refused to spawn (%s)",
                root,
                ProcessGuardError.ExecDisabled,
            )
            return False
        result = guarded.danger_ok
        if result.returncode != 0:
            _log.warning(
                "land: `make core` in %s exited %d -- stdout=%r stderr=%r",
                root,
                result.returncode,
                result.stdout[-2000:],
                result.stderr[-2000:],
            )
        return result.returncode == 0

    return fn


def _land(root: Path, cfg: AppConfig) -> None:
    """`frob ticket land <id> --worktree <path> [--dry-run]`: run the whole
    merge-check-splice-close-commit chain via `frob.tickets.land`, reporting
    every field of the resulting `LandReport` (or the exact `Err` + remedy
    already logged by `land` itself) before exiting non-zero on failure.

    T-0398: this is the CLI's STRICT default -- `collected`/`passed`/
    `covers_scope` are ALWAYS supplied (as closures over the worktree,
    since `land`'s internal merge determines the post-merge state they
    must be computed against, see `land`'s own docstring), so a stale/
    red/unrelated evidence id can never silently land onto main through
    the real `frob ticket land` command, even though the library function
    itself still defaults to permissive (`None`) for other callers/tests.

    T-0338: `bump_version`/`rebuild_natives` are ALSO always supplied here
    (`_land_bump_version_fn`/`_land_rebuild_natives_fn`), folding the
    REL001 version-bump/stamp and native-rebuild-trigger coordinator steps
    into this same one command.

    T-0754: `check_gates` (`_check_gates_summary_fn`, the SAME closure
    `_done_report` captures with) is ALSO always supplied here, so a
    ticket carrying a `### Captured claims` section is re-verified against
    the post-merge tree before `frob ticket land` ever finalizes/closes/
    squash-applies it. The claim's test-count half reuses `passed` above
    -- no separate `run_tests` parameter at the land layer (review round 2
    fix #3: derive from D-05's own real run instead of a duplicate one)."""
    from frob.tickets import land

    _require_land_args(cfg)
    assert cfg.ticket_id is not None  # narrows for the type checker; enforced above
    assert cfg.ticket_worktree is not None
    worktree = cfg.ticket_worktree

    if cfg.ticket_skip_mutation_evidence:
        _log.warning(
            "ticket land: %s --skip-mutation-evidence set -- a TEST016 "
            "confirmatory-only-evidence finding will be logged but will NOT "
            "refuse this land (justification required: use only for a "
            "genuine false positive)",
            cfg.ticket_id,
        )

    result = land(
        root,
        cfg.ticket_id,
        worktree,
        dry_run=cfg.ticket_dry_run,
        collected=_land_collected_fn(worktree),
        passed=_land_passed_fn(worktree),
        covers_scope=_land_covers_scope_fn(worktree),
        bump_version=_land_bump_version_fn(),
        rebuild_natives=_land_rebuild_natives_fn(),
        check_gates=_check_gates_summary_fn(worktree, cfg.ticket_id),
        check_gate_findings=_check_gate_findings_fn(worktree, cfg.ticket_id),
        skip_mutation_evidence=cfg.ticket_skip_mutation_evidence,
    )
    if result.is_err:
        _log.error("ticket land failed: %s", result.danger_err)
        sys.exit(1)

    _report_land_result(root, result.danger_ok)


# frob:ticket T-0323
def _require_merge_driver_args(cfg: AppConfig) -> None:
    """Exit 1 (with a logged reason) unless `frob ticket merge-driver`'s
    three positional temp-file paths (%O/%A/%B, git's merge-driver
    protocol) are all present."""
    if (
        cfg.ticket_merge_base is None
        or cfg.ticket_merge_ours is None
        or cfg.ticket_merge_theirs is None
    ):
        _log.error(
            "frob ticket merge-driver requires %%O %%A %%B (base/ours/theirs "
            "temp file paths -- git supplies these when invoked as the "
            "registered merge driver, see .gitattributes / docs/modules/"
            "tickets.md#git-merge-driver)"
        )
        sys.exit(1)


# frob:ticket T-0323
def _merge_driver(root: Path, cfg: AppConfig) -> None:
    """`frob ticket merge-driver %O %A %B`: git's merge-driver entry point
    for `tickets.md` (docs/modules/tickets.md#git-merge-driver). Reads the
    `ours` (%A) and `theirs` (%B) temp files git hands it, splices them via
    the SAME `splice_ledger` `frob ticket land` uses (never a duplicate
    reimplementation), and overwrites `ours` in place with the result --
    the merge-driver protocol's contract: `ours`'s final content on disk
    IS the merge result git commits, regardless of exit status. `base`
    (%O) is accepted (git always supplies it) but unused: `splice_ledger`
    resolves per-ticket-id divergence via state-rank/Done-report tiebreaks
    over `ours`/`theirs` alone, the same as `land`'s own splice call, not
    a 3-way base diff. Exits 0 (git treats the auto-splice as a clean,
    non-conflicted merge) unless `ours`/`theirs` fail to parse as a
    ticket ledger, in which case it exits 1 and leaves `ours` untouched --
    git then reports the usual conflict for a human to resolve by hand,
    exactly as if no driver were registered."""
    from frob.tickets import splice_ledger
    from frob.tickets._land import _archived_ids

    _require_merge_driver_args(cfg)
    assert cfg.ticket_merge_ours is not None  # narrows for the type checker
    assert cfg.ticket_merge_theirs is not None
    ours_path, theirs_path = cfg.ticket_merge_ours, cfg.ticket_merge_theirs

    ours_text = ours_path.read_text(encoding="utf-8")
    theirs_text = theirs_path.read_text(encoding="utf-8")

    spliced = splice_ledger(ours_text, theirs_text, archived_ids=_archived_ids(root))
    if spliced.is_err:
        _log.error(
            "ticket merge-driver: splice_ledger failed (%s) -- leaving %s "
            "untouched for a manual conflict resolution",
            spliced.danger_err,
            ours_path,
        )
        sys.exit(1)

    ours_path.write_text(spliced.danger_ok, encoding="utf-8")
    _log.info(
        "ticket merge-driver: spliced %s (ours) + %s (theirs) -> %s",
        ours_path,
        theirs_path,
        ours_path,
    )


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


# frob:ticket T-0472
def _requeue(root: Path, cfg: AppConfig) -> None:
    """Transition an in-progress ticket back to queued (the state-machine-
    legal reverse of `start`'s auto-plan+start), for a parked or
    mis-started ticket that must be honestly requeued instead of hand-
    edited (T-0472). Since the T-0453 tree-lease is derived live from
    IN_PROGRESS state + scope, this transition alone releases the lease --
    no separate lease-release step is needed. `--reason` is optional and,
    when given, is only logged (not persisted) -- requeue carries no
    Done-report/evidence surface of its own to attach it to."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket requeue requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="requeue")
    if ticket.state != TicketState.IN_PROGRESS:
        _log.error(
            "ticket requeue failed: %s is %s, not in-progress -- only an "
            "in-progress ticket can be requeued",
            cfg.ticket_id,
            ticket.state.value,
        )
        sys.exit(1)

    requeued = transition(root, cfg.ticket_id, TicketState.QUEUED)
    if requeued.is_err:
        _log.error("ticket requeue failed: %s", requeued.danger_err)
        sys.exit(1)
    if cfg.ticket_reason:
        _log.info(
            "%s requeued (in-progress -> queued): %s",
            cfg.ticket_id,
            cfg.ticket_reason,
        )
    else:
        _log.info("%s requeued (in-progress -> queued)", cfg.ticket_id)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="requeued")


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


def _find_landing_commit(root: Path, ticket_id: str) -> str | None:
    """The short hash of the commit that landed `ticket_id`, if cheaply
    derivable (T-0835) -- `frob ticket land`'s own commits are conventionally
    titled `land <id> ...` (see this repo's own git history), so a `git log
    --grep` for that exact phrase against `root` finds it in one spawn. Best-
    effort: `None` on any git failure, an empty result, or a non-repo `root`
    -- a terminal-state refusal must still fire even when the commit cannot
    be named, just without the extra detail."""
    from frob import gitio

    spawned = gitio.run_argv(
        (
            "git",
            "-C",
            str(root),
            "log",
            "--oneline",
            "-E",
            "--grep",
            f"land {ticket_id}([^0-9]|$)",
            "-n",
            "1",
        )
    )
    if spawned.is_err:
        return None
    line = spawned.danger_ok.stdout.strip()
    if not line:
        return None
    return line.split(maxsplit=1)[0]


def _refuse_if_terminal(root: Path, ticket_id: str, ticket) -> None:  # noqa: ANN001
    """`sys.exit(1)` with an actionable message if `ticket` is DONE or
    DROPPED (T-0835): re-`start`ing a terminal ticket is never legitimate --
    the T-0835 incident was exactly a second agent's `start` succeeding on a
    ticket another worktree had already finished. Names the landing commit
    when `_find_landing_commit` can cheaply find one; otherwise names just
    the terminal state, never blocking the refusal on git being unavailable."""
    from frob.tickets import TicketState

    if ticket.state not in (TicketState.DONE, TicketState.DROPPED):
        return
    commit = (
        _find_landing_commit(root, ticket_id)
        if ticket.state is TicketState.DONE
        else None
    )
    if commit is not None:
        _log.error(
            "ticket start failed: %s is already %s (landed at %s) -- nothing to start",
            ticket_id,
            ticket.state.value,
            commit,
        )
    else:
        _log.error(
            "ticket start failed: %s is already %s -- nothing to start",
            ticket_id,
            ticket.state.value,
        )
    sys.exit(1)


def _refuse_if_foreign_live_lease(root: Path, ticket_id: str, *, steal: bool) -> None:
    """`sys.exit(1)` if `ticket_id` holds a LIVE lease pinned to a worktree
    other than `root`, unless `steal` is set (T-0835 -- the double-dispatch
    fix). A lease pinned to `root` itself is idempotent (no refusal, so a
    restart after an interrupted session in the SAME worktree keeps
    working); an EXPIRED lease (`is_lease_ttl_expired`) never blocks --
    that is the existing dead-agent recovery path (T-0782/T-0476) and must
    stay intact.

    Stealing does not itself rewrite the lease file: the caller's own
    `transition(..., TicketState.IN_PROGRESS)` call (via `_sync_cross_
    worktree_lease`) already re-`record_lease`s pinned to `root`
    unconditionally, which overwrites the stolen worktree's file in place --
    reusing that existing machinery rather than inventing a second lease
    write path. The losing worktree's OWN lease is gone the moment this
    returns, so its later `resolve_lease`/`ticket_lease_pin` (`frob check
    --ticket`, `frob ticket close`) fails against the new content, exactly
    the "cannot silently land" property T-0835 requires."""
    from frob.tickets._leases import (
        is_lease_ttl_expired,
        lease_age_seconds,
        read_all_leases,
    )

    record = next((r for r in read_all_leases(root) if r.ticket_id == ticket_id), None)
    if record is None or is_lease_ttl_expired(record):
        return
    record_worktree = Path(record.worktree).resolve()
    if record_worktree == root.resolve():
        return

    age = lease_age_seconds(record)
    age_desc = f"{age:.0f}s ago" if age is not None else "unknown age"
    if steal:
        _log.warning(
            "ticket start: %s stealing live lease from worktree %s "
            "(recorded %s) -- that worktree's lease is now invalidated and "
            "cannot close/land %s",
            ticket_id,
            record_worktree,
            age_desc,
            ticket_id,
        )
        return
    _log.error(
        "ticket start failed: %s has a live lease held by worktree %s "
        "(recorded %s) -- pass --steal to override (this invalidates the "
        "other worktree's lease so it can no longer close/land %s)",
        ticket_id,
        record_worktree,
        age_desc,
        ticket_id,
    )
    sys.exit(1)


def _start(root: Path, cfg: AppConfig) -> None:
    """Transition to in-progress (auto-planning a queued ticket first) and
    run the pre-work sweep. Starting a ticket that is ALREADY in-progress is
    a hard error, not a silent no-op or refresh (T-0215): `frob ticket
    sweep <id>` already exists as the idempotent refresh path, so re-running
    `start` on an in-progress ticket is treated as a coordinator mistake and
    named explicitly, pointing at `sweep` instead of quietly duplicating it.

    T-0835: also refuses (a) a ticket already in a terminal state (done/
    dropped) and (b) a ticket holding a LIVE lease pinned to a DIFFERENT
    worktree, both before the in-progress check above -- either can be true
    while this worktree's OWN ledger view still shows an earlier state (the
    double-dispatch incident this ticket fixes), so both must be checked
    independently of local ticket state. `--steal` (`cfg.ticket_steal`)
    overrides (b) only; (a) has no override, a terminal ticket is never
    restartable."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket start requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="start")
    _refuse_if_terminal(root, cfg.ticket_id, ticket)
    _refuse_if_foreign_live_lease(root, cfg.ticket_id, steal=cfg.ticket_steal)

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
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="started")

    # frob:ticket T-0474
    # By default `start` is now just the state transition above -- the
    # pre-work sweep (a synchronous whole-repo dup+xref scan, 57s on this
    # repo's /mnt/c checkout) runs in the BACKGROUND instead of blocking the
    # command. `--foreground` opts back into the old synchronous behavior
    # (useful for a script/test that wants the sweep guaranteed recorded the
    # instant `start` returns). Either way, `frob ticket sweep <id>` remains
    # the always-available, always-synchronous way to (re)record it, so
    # PRE001 stays satisfiable regardless of how `start` recorded it.
    if cfg.ticket_foreground:
        _run_sweep(root, transitioned.danger_ok)
    else:
        _spawn_background_sweep(root, cfg.ticket_id)


def _spawn_background_sweep(root: Path, ticket_id: str) -> None:
    """Launch `frob ticket sweep <ticket_id>` as a detached background
    process against `root` (T-0474) -- `start` returns as soon as this is
    spawned, without waiting for the sweep (dup scan + xref + scope digest)
    to finish. `start_new_session=True` detaches it from this process's
    session so it keeps running after the `start` CLI invocation exits;
    stdout/stderr are discarded (the sweep's own `record_prework` call is
    the durable side effect a caller cares about -- `frob check`'s PRE001
    gate, or a later `frob ticket sweep`/`frob ticket show`, is how a
    caller observes whether it has landed yet, not this process's output).

    Best-effort: if spawning itself fails (e.g. `sys.executable` refused by
    a locked-down sandbox), this logs a warning and falls back to running
    the sweep synchronously right here -- `start` must never silently skip
    recording a sweep at all, only ever trade "instant" for "eventually".

    Honors the repo-wide exec kill switch (`FROB_DISABLE_EXEC`, T-0200):
    when set, no process is spawned at all and the sweep runs
    synchronously in-process, keeping `may "exec"` on the `cli` node a
    genuinely switchable capability (design/frob.strata, T-0474)."""
    if not exec_enabled():
        _log.info(
            "ticket start: %s exec kill switch (%s) set -- running the "
            "pre-work sweep synchronously in-process",
            ticket_id,
            EXEC_KILL_SWITCH_ENV,
        )
        ticket = _load_ticket_or_exit(root, ticket_id, verb="start")
        _run_sweep(root, ticket)
        return
    try:
        subprocess.Popen(  # noqa: S603
            [
                sys.executable,
                "-m",
                "frob",
                "ticket",
                "sweep",
                ticket_id,
                "--path",
                str(root),
            ],
            cwd=str(root),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError as exc:
        _log.warning(
            "ticket start: %s background sweep spawn failed (%s) -- "
            "running it synchronously instead",
            ticket_id,
            exc,
        )
        ticket = _load_ticket_or_exit(root, ticket_id, verb="start")
        _run_sweep(root, ticket)
        return
    _log.info(
        "ticket start: %s pre-work sweep launched in the background -- "
        "`frob ticket sweep %s` re-runs it synchronously if needed sooner",
        ticket_id,
        ticket_id,
    )


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


# frob:ticket T-0476
def _reconcile_cmd(root: Path, cfg: AppConfig) -> None:
    """`frob ticket reconcile [--apply] [--remove-orphans]`: report (and,
    with `--apply`, heal) T-0476's two ticket<->worktree binding anomalies,
    plus T-0456's orphaned-`land`-intent anomaly. Always logs a
    human-readable summary; exits 0 whether or not anomalies were found
    (finding an anomaly is not itself a command failure -- only a real
    error loading the ledger is)."""
    from frob.tickets import reconcile

    result = reconcile(
        root,
        apply=cfg.ticket_reconcile_apply,
        remove_orphans=cfg.ticket_reconcile_remove_orphans,
    )
    if result.is_err:
        _log.error("ticket reconcile failed: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    verb = "requeued" if report.applied else "would requeue"
    if report.requeued_tickets:
        _log.info(
            "reconcile: %s %d stale in-progress hold(s): %s",
            verb,
            len(report.requeued_tickets),
            list(report.requeued_tickets),
        )
    else:
        _log.info("reconcile: no stale in-progress holds found")

    if report.orphan_worktrees:
        removed_verb = "removed" if report.removed_orphans else "flagged (not removed)"
        _log.info(
            "reconcile: %s %d orphan worktree(s) (no lease): %s",
            removed_verb,
            len(report.orphan_worktrees),
            list(report.orphan_worktrees),
        )
    else:
        _log.info("reconcile: no orphan worktrees found")

    if report.orphaned_land_intents:
        intent_verb = "cleared" if report.applied else "would clear"
        _log.info(
            "reconcile: %s %d orphaned land intent(s) (crash/interrupt mid-land): %s",
            intent_verb,
            len(report.orphaned_land_intents),
            list(report.orphaned_land_intents),
        )
    else:
        _log.info("reconcile: no orphaned land intents found")


# frob:ticket T-0354
# frob:tests tests/unit/test_app_runners_batch7.py::TestTicketStart.test_start_foreground_runs_sweep_synchronously  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_spawns_detached_sweep_subprocess  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_popen_failure_falls_back_to_synchronous_sweep  # noqa: E501
# frob:tests tests/unit/test_app_runners_batch7.py::TestSpawnBackgroundSweep.test_exec_kill_switch_forces_synchronous_sweep  # noqa: E501
def _run_sweep(root: Path, ticket) -> None:  # noqa: ANN001
    """Record the pre-work sweep (dup + xref + scope digest) for `ticket`.

    Delegates to `frob.gates.sweep_ticket` (T-0236's flagged follow-up,
    closed by T-0354): this call site used to carry its own copy of the
    xref loop with the same two bugs `sweep_ticket` fixed for T-0240 -- an
    unbounded `xref(symbol, root)` re-walk of the WHOLE tree per scope
    glob regardless of the per-pattern scan path, and a
    `Path(pattern).stem` guess that fed glob syntax (`"**"`, `"__init__"`)
    into xref as if it were a real symbol name. `src/frob/app/**` was out
    of scope for T-0240, so this copy kept both bugs live until now;
    delegating collapses the duplication instead of porting a second copy
    of the same fix.
    """
    from frob.gates import sweep_ticket

    swept = sweep_ticket(root, ticket)
    if swept.is_err:
        _log.error("pre-work sweep recording failed: %s", swept.danger_err)
        sys.exit(1)

    sweep = swept.danger_ok
    _log.info(
        "swept %s: dup_findings=%d xref_hits=%d",
        ticket.id,
        sweep.dup_findings,
        len(sweep.xref_hits),
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
    if err == TicketError.AcceptanceUnbound:
        return (
            f"close failed: {err} -- see the WARNING line above naming "
            f"which acceptance criterion/criteria still have no resolving "
            f"evidence id; bind one with `frob ticket evidence {ticket_id} "
            f"<node-id> --accepts <index>` (0-based, per "
            f"`frob ticket show {ticket_id}`'s acceptance list)"
        )
    if err == TicketError.MissingApprovedReview:
        return (
            f"close failed: {err} -- {ticket_id} needs an approve-verdict "
            f"review naming the current commit (`frob ticket review "
            f"{ticket_id} --verdict approve --reviewer NAME --findings-file "
            f"PATH`) before `close --strict` will succeed"
        )
    return f"close failed: {err}"


# frob:ticket T-0398
def _graph_snapshot(root: Path):  # noqa: ANN201
    """The current `GraphSnapshot`, loading the cache (or building it fresh
    on a miss) -- same pattern as `_scope_digest_for_ticket`, factored so
    D-02's `covers_scope` computation shares it rather than re-deriving
    its own cache-then-build fallback."""
    from frob.graph import build_graph, load_graph

    cache = root / _CACHE_REL
    loaded = load_graph(cache)
    if loaded.is_err:
        loaded = build_graph(root, cache)
    return loaded


# frob:ticket T-0398
def _covers_scope_for_ticket(root: Path, ticket) -> bool | None:  # noqa: ANN001
    """D-02 CLI wiring: whether `ticket`'s evidence covers a touched/scope
    symbol, via `frob.gates.evidence_covers_scope` over the current graph.

    Returns `None` (skip the check entirely) when `ticket` carries NO
    non-cmd evidence at all -- a docs-kind ticket closed purely via
    `--evidence-cmd` has its own separate exit-code/digest verification
    channel (`add_cmd_evidence`) that already substitutes for "coverage";
    `evidence_covers_scope` would otherwise (correctly, by its own
    contract) return `False` for a ticket with zero non-cmd evidence to
    scan, which would wrongly block the docs cmd-evidence path this ticket
    was explicitly warned not to break. Also returns `None` when
    `ticket.scope` itself is empty -- an undeclared scope gives the
    binding check nothing to bind AGAINST, so "does evidence cover scope"
    is not a meaningful question to ask (this is a false-positive guard,
    not a loophole: a ticket that declares a real scope still gets the
    full check). Returns `False` (fail-closed, blocking the close) if the
    graph itself cannot be loaded/built -- "cannot verify" must never
    silently become "verified"."""
    from frob.gates import evidence_covers_scope
    from frob.tickets._models import is_cmd_evidence

    non_cmd = [e for e in ticket.evidence if not is_cmd_evidence(e)]
    if not non_cmd or not ticket.scope:
        return None

    snapshot = _graph_snapshot(root)
    if snapshot.is_err:
        _log.warning(
            "ticket close: graph unavailable (%s), cannot verify D-02 "
            "scope-binding -- refusing to close on unverifiable evidence",
            snapshot.danger_err,
        )
        return False
    return evidence_covers_scope(ticket, snapshot.danger_ok)


# frob:ticket T-0571
def _current_commit(root: Path) -> str | None:
    """Best-effort `git rev-parse HEAD` under `root` (`None` on any git
    failure) -- shared by `_review`'s default `--commit` and `_close`'s
    strict-mode gate so both name the SAME notion of "current commit"."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


# frob:ticket T-0571
# frob:doc docs/modules/tickets.md#public-api
# frob:tests tests/test_tickets_review.py::TestReviewCli.test_cli_writes_review_record
# frob:tests tests/test_tickets_review.py::TestReviewCli.test_cli_requires_all_flags
def _review(root: Path, cfg: AppConfig) -> None:
    """`frob ticket review <id> --verdict approve|reject --reviewer NAME
    --findings-file PATH [--commit SHA]`: resolve the findings text and
    commit, then call `frob.tickets.record_review` -- the structured,
    first-class adversarial-review evidence channel (T-0571). `--commit`
    defaults to the current `HEAD` under `root` when omitted."""
    from frob.tickets import ReviewVerdict, record_review

    if (
        cfg.ticket_id is None
        or cfg.ticket_review_verdict is None
        or cfg.ticket_reviewer is None
        or cfg.ticket_findings_file is None
    ):
        _log.error(
            "frob ticket review requires <id> --verdict approve|reject "
            "--reviewer NAME --findings-file PATH"
        )
        sys.exit(1)

    try:
        findings = cfg.ticket_findings_file.read_text(encoding="utf-8")
    except OSError as exc:
        _log.error(
            "review: could not read --findings-file %s: %s",
            cfg.ticket_findings_file,
            exc,
        )
        sys.exit(1)

    commit = cfg.ticket_review_commit or _current_commit(root)
    if commit is None:
        _log.error(
            "review: could not resolve --commit and no --commit was given "
            "(is %s a git checkout?)",
            root,
        )
        sys.exit(1)

    result = record_review(
        root,
        cfg.ticket_id,
        verdict=ReviewVerdict(cfg.ticket_review_verdict),
        reviewer=cfg.ticket_reviewer,
        findings=findings,
        commit=commit,
    )
    if result.is_err:
        _log.error("review failed: %s", result.danger_err)
        sys.exit(1)
    _log.info(
        "%s: recorded review verdict=%s reviewer=%s commit=%s",
        cfg.ticket_id,
        cfg.ticket_review_verdict,
        cfg.ticket_reviewer,
        commit,
    )


# frob:ticket T-0571
def _covers_review_for_ticket(root: Path, cfg: AppConfig, ticket) -> bool | None:  # noqa: ANN001
    """T-0571's CLI-side strict-mode predicate: `None` (skip the check)
    unless BOTH `--strict` was passed on this `close` invocation AND
    `[tickets] require_review_for_close` is true in `frob.toml` -- either
    condition missing means "not opted in", never a silent enforcement.
    When both are true, resolves the current commit and asks
    `frob.tickets.has_approved_review_for_commit`."""
    from frob.tickets import (
        has_approved_review_for_commit,
        load_require_review_for_close,
    )

    if not cfg.ticket_close_strict or not load_require_review_for_close(root):
        return None
    commit = _current_commit(root)
    if commit is None:
        _log.warning(
            "ticket close --strict: could not resolve current commit under "
            "%s -- refusing to close on unverifiable review",
            root,
        )
        return False
    return has_approved_review_for_commit(ticket, commit)


# frob:ticket T-0106
# frob:ticket T-0215
# frob:ticket T-0398
# frob:ticket T-0571
def _close(root: Path, cfg: AppConfig) -> None:
    """Transition a ticket to done; if `--evidence` ids or `--evidence-cmd`
    were given, validate and append them first (`_apply_evidence` /
    `_apply_cmd_evidence`) and refuse to transition at all if either is
    unresolvable/fails, so a bad flag can never close a ticket on
    unvalidated evidence. A failed transition is reported through
    `_close_failure_hint` so the operator gets a concrete next command, not
    just the bare state-machine error (T-0215).

    T-0398: this is the CLI's STRICT default -- `covers_scope` is always
    computed (`_covers_scope_for_ticket`) and always passed to
    `transition`, so evidence that covers none of the ticket's touched/
    scope symbols rejects the close (`EvidenceScopeUnbound`) through the
    real `frob ticket close` command.

    T-0571: `reviewed` is only ever non-`None` when BOTH `--strict` was
    passed AND `[tickets] require_review_for_close` is true in
    `frob.toml` (`_covers_review_for_ticket`) -- config-gated, off by
    default, so this never breaks a repo/workflow that has not opted in."""
    from frob.tickets import TicketState, transition

    if cfg.ticket_id is None:
        _log.error("frob ticket close requires <id>")
        sys.exit(1)

    ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")

    if cfg.ticket_evidence_ids:
        added = _apply_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_ids, cfg.ticket_accepts
        )
        if added.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_added = _apply_cmd_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_cmd, cfg.ticket_accepts
        )
        if cmd_added.is_err:
            sys.exit(1)

    # Re-load: evidence may have just changed above, and covers_scope must
    # be computed against the ticket's CURRENT evidence, not the state
    # loaded before this call's own --evidence/--evidence-cmd applied.
    fresh_ticket = _load_ticket_or_exit(root, cfg.ticket_id, verb="close")
    covers_scope = _covers_scope_for_ticket(root, fresh_ticket)
    reviewed = _covers_review_for_ticket(root, cfg, fresh_ticket)

    result = transition(
        root,
        cfg.ticket_id,
        TicketState.DONE,
        covers_scope=covers_scope,
        reviewed=reviewed,
    )
    if result.is_err:
        _log.error(_close_failure_hint(cfg.ticket_id, ticket.state, result.danger_err))
        sys.exit(1)
    _log.info("%s closed (done)", cfg.ticket_id)
    # frob:ticket T-0178
    from frob.app.telemetry import record_ticket_event

    record_ticket_event(root, ticket_id=cfg.ticket_id, event="done")


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


# frob:ticket T-0579
def _drop(root: Path, cfg: AppConfig) -> None:
    """CLI wiring for `frob ticket drop <id> --reason TEXT [--absorbed-by
    T-####]` (T-0579): the first-class replacement for hand-editing
    `state: dropped` directly. Delegates entirely to `frob.tickets.
    drop_ticket` for the reason-line + transition + lease-release
    mechanics; this layer only validates required args and reports the
    Result."""
    from frob.tickets import drop_ticket

    if cfg.ticket_id is None or not cfg.ticket_reason:
        _log.error("frob ticket drop requires <id> and --reason")
        sys.exit(1)

    result = drop_ticket(
        root, cfg.ticket_id, cfg.ticket_reason, absorbed_by=cfg.ticket_absorbed_by
    )
    if result.is_err:
        _log.error("drop failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s dropped", cfg.ticket_id)


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
        result = _apply_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_ids, cfg.ticket_accepts
        )
        if result.is_err:
            sys.exit(1)

    if cfg.ticket_evidence_cmd:
        cmd_result = _apply_cmd_evidence(
            root, cfg.ticket_id, cfg.ticket_evidence_cmd, cfg.ticket_accepts
        )
        if cmd_result.is_err:
            sys.exit(1)


# frob:ticket T-0458
def _resolve_done_report_why(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket done-report`'s narrative why text: `--why-file`
    wins if given, else `--why` (a literal `-` or an omitted value both
    mean "read stdin", so `frob ticket done-report T-#### -` and a bare
    `frob ticket done-report T-####` piped a narrative both work). Exits 1
    on an unreadable `--why-file`; returns `None` only if reading stdin
    yields nothing meaningful for the caller to act on (never silently
    writes an empty report)."""
    if cfg.ticket_why_file is not None:
        try:
            return cfg.ticket_why_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "done-report: could not read --why-file %s: %s",
                cfg.ticket_why_file,
                exc,
            )
            sys.exit(1)
    if cfg.ticket_why is not None and cfg.ticket_why != "-":
        return cfg.ticket_why
    text = sys.stdin.read()
    return text or None


# frob:ticket T-0754
# frob:ticket T-0754
# The `gate-summary` tool line's leading counts, e.g. "0 errors, 3
# warnings, 12 waived" -- deliberately does NOT match the trailing
# `[archgate=7.99s, ...]` per-gate timing blob `_gate_summary_result`
# appends after it, since that blob is wall-clock and therefore different
# on every single invocation even against an IDENTICAL tree (T-0754 review
# round 2's FATAL fix: a strict-equality re-verification against the RAW
# summary LINE, timing blob included, refused every land, including this
# ticket's own).
_GATE_SUMMARY_COUNTS_RE = re.compile(
    r"gate-summary\s+(\d+)\s+errors?,\s+(\d+)\s+warnings?,\s+(\d+)\s+waived"
)


# frob:ticket T-0846
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree kind="unit"  # noqa: E501
def _python_for_tree(root: Path) -> str:
    """The interpreter that runs `root`'s OWN installed code (T-0846): the
    checked-out tree's `.venv/bin/python` when it exists there, else
    `sys.executable` (the CALLING process's own interpreter) as a
    fallback.

    T-0846: `_check_gates_summary_fn`/`_check_gate_findings_fn` used to
    spawn `sys.executable -m frob check` unconditionally -- whatever
    interpreter the CALLING process happened to run under, not the tree
    being checked. `done-report` capture runs from inside the worktree (its
    own venv, an editable install of the worktree's OWN code); `land`
    re-verification runs from the ROOT checkout (root's venv, `main`'s
    code) but against `root`'s post-merge tree. For a ticket that adds or
    removes a public surface a gate validates against the LIVE, running
    registry (T-0441: a ticket adding a `frob fmt` subcommand), the
    root-venv fresh check's `frob` package has no `fmt` in its own live
    `_build_parser` at all, so a gate that cross-checks a doc/registry
    surface against that live registry (T-0441's concrete reproduction:
    DOC005, README rows naming `frob fmt` as a subcommand "that no longer
    exists" -- 34 rows recorded at capture time vs 33 seen fresh) fires
    deterministically post-merge even though the capture legitimately saw
    zero. `refresh-done-report-and-retry` can never converge for this
    class -- the two runs are checking two DIFFERENT installed trees'
    code, not two views of the same one. Resolving the interpreter from
    `root` itself closes this: both capture and re-verification always run
    the CHECKED tree's own installed code, matching what `uv run frob
    check` would do if invoked there directly.

    Falls back to `sys.executable` (never a hard error) when `root` has no
    `.venv/bin/python` -- a bare checkout with no venv of its own yet, or a
    non-uv-managed tree -- so this is strictly a refinement of the prior
    unconditional `sys.executable`, never a new failure mode."""
    venv_python = root / ".venv" / "bin" / "python"
    if venv_python.is_file():
        return str(venv_python)
    return sys.executable


# frob:ticket T-0754
# frob:ticket T-0832
# frob:ticket T-0846
# frob:tests tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_report_then_land_succeeds kind="integration"  # noqa: E501
# frob:tests tests/unit/test_ticket_runner_gate_findings.py::TestPythonForTree kind="unit"  # noqa: E501
def _check_gates_summary_fn(root: Path, ticket_id: str):  # noqa: ANN201
    """CLI closure shared by `done-report` capture and `land` re-
    verification (T-0754): calling it spawns a fresh `python -m frob check
    --ticket <id>` in `root` and returns `(errors, warnings, waived)` --
    the `gate-summary` line's own COUNTS, parsed via `_GATE_SUMMARY_COUNTS_
    RE`, never that line's raw text (whose timing blob is nondeterministic
    -- see the regex's own doc) and never composed or retyped by this
    layer. Routed through `guarded_subprocess_run` (T-0778's guard) so
    `FROB_DISABLE_EXEC=1` refuses this spawn too. A refused spawn, a hard
    subprocess failure, or unparsable output returns `None` (T-0832) --
    never a `(-1, -1, -1)` sentinel. A real `frob check` run can never
    produce a negative count, but a fixed sentinel is still a VALUE: it
    compares equal to another sentinel of the same shape, which let a
    land re-verification (`_land.py`'s
    `_reverify_done_report_claims_post_merge`) PASS vacuously when both
    the captured claim and the fresh post-merge check were unmeasurable
    for unrelated reasons (the T-0830 incident: a self-closed, lease-
    released ticket's done-report capture and land's own post-merge check
    both failed to run, both recorded `-1`, and `-1 == -1` read as "no
    divergence"). `None` cannot silently compare equal to a measured
    triple, so every caller is forced to branch on "unmeasured"
    explicitly instead."""

    def fn() -> tuple[int, int, int] | None:
        guarded = guarded_subprocess_run(
            [_python_for_tree(root), "-m", "frob", "check", "--ticket", ticket_id],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if guarded.is_err:
            _log.warning(
                "ticket %s: `frob check --ticket %s` refused to spawn (%s)",
                ticket_id,
                ticket_id,
                ProcessGuardError.ExecDisabled,
            )
            return None
        result = guarded.danger_ok
        match = _GATE_SUMMARY_COUNTS_RE.search(result.stdout)
        if match is None:
            _log.warning(
                "ticket %s: `frob check --ticket %s` output had no "
                "parsable gate-summary line (exit=%d) -- gate state is "
                "unmeasured, not zero",
                ticket_id,
                ticket_id,
                result.returncode,
            )
            return None
        errors, warnings, waived = (int(g) for g in match.groups())
        return (errors, warnings, waived)

    return fn


# frob:ticket T-0846
# T-0846: one printed error-diagnostic line's shape, e.g.
# "  [gate:SCOPE] src/frob/tickets/_land.py:0  SCOPE001  SCOPE001: message"
# (`frob.check._section_lines`'s `f"  [{tool}] {d.as_text()}"`, `Diagnostic.
# as_text`'s own `file:line  CODE  message` rendering) -- captures the file
# and rule-id code, deliberately not the message (whose wording can change
# without the finding's identity changing).
_GATE_ERROR_LINE_RE = re.compile(
    r"^\s*\[[^\]]*\]\s+(?P<file>\S+?):\d+\s+(?P<code>[A-Za-z][A-Za-z0-9]*)\s"
)


# frob:ticket T-0846
# frob:tests tests/test_ticket_land.py::TestDoneReportThenLandRealClosuresEndToEnd.test_real_closures_done_report_then_land_succeeds kind="integration"  # noqa: E501
def _check_gate_findings_fn(root: Path, ticket_id: str):  # noqa: ANN201
    """CLI closure (T-0846, sibling to `_check_gates_summary_fn`): calling it
    spawns a fresh `python -m frob check --ticket <id>` in `root` (its own
    subprocess, NOT shared with `_check_gates_summary_fn`'s -- a documented
    doubled-cost tradeoff, see the module-level note this function's own
    docstring references, kept for correctness-first simplicity) and
    returns a `frozenset[(rule_id, file)]` recovered from every `## Errors`
    diagnostic line the run printed -- the per-finding IDENTITY set
    `_reverify_done_report_claims_post_merge` compares instead of a raw
    count, closing the masking gap a scope-wide count alone cannot close
    (a land's own diff introducing N new errors sailing through whenever
    an unrelated fix on the same branch removed more than N). Routed
    through `guarded_subprocess_run` (T-0778's guard), same as
    `_check_gates_summary_fn`. A refused spawn or a hard subprocess
    failure returns `None` (unmeasured, never an empty-set false claim of
    "definitely zero") -- `_reverify_done_report_claims_post_merge` falls
    back to the count-only comparison in that case.

    Cost note: today this is a SECOND full `frob check --ticket` spawn
    whenever both this and `_check_gates_summary_fn` are wired to the same
    land/done-report call -- deduplicating the two into one shared
    subprocess run is a real, known follow-up (not silently dropped; see
    the Done report and the extended T-0850 scope), left for a
    later pass so this fix lands correctness-first."""

    def fn() -> frozenset[tuple[str, str]] | None:
        guarded = guarded_subprocess_run(
            [_python_for_tree(root), "-m", "frob", "check", "--ticket", ticket_id],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        if guarded.is_err:
            _log.warning(
                "ticket %s: `frob check --ticket %s` refused to spawn for "
                "error-finding identities (%s)",
                ticket_id,
                ticket_id,
                ProcessGuardError.ExecDisabled,
            )
            return None
        result = guarded.danger_ok
        section = result.stdout.split("## Errors", 1)
        if len(section) < 2:
            # No "## Errors" heading at all means zero error diagnostics
            # were printed this run (`_section_lines` omits an empty
            # section entirely) -- a real, measured empty set, not
            # "unmeasured": the gate-summary line's own error count (parsed
            # by `_GATE_SUMMARY_COUNTS_RE`) is the cross-check that this is
            # genuinely zero rather than a parse miss.
            if _GATE_SUMMARY_COUNTS_RE.search(result.stdout) is None:
                _log.warning(
                    "ticket %s: `frob check --ticket %s` output had no "
                    "parsable gate-summary line at all (exit=%d) -- "
                    "error-finding identities are unmeasured, not "
                    "necessarily zero",
                    ticket_id,
                    ticket_id,
                    result.returncode,
                )
                return None
            return frozenset()
        after_heading = section[1].split("\n\n", 1)[0]
        findings: set[tuple[str, str]] = set()
        for line in after_heading.splitlines():
            match = _GATE_ERROR_LINE_RE.match(line)
            if match:
                findings.add((match.group("code"), match.group("file")))
        return frozenset(findings)

    return fn


# frob:ticket T-0754
def _run_tests_count_fn(root: Path):  # noqa: ANN201
    """CLI closure shared by `done-report` capture and `land` re-
    verification (T-0754): calling it with a sequence of non-cmd evidence
    node ids actually RUNS them (reusing `_verify_ids_passing`, D-01's
    same real-run verification) and returns the count that ACTUALLY
    passed -- never the length of the input, so a divergence between
    "claimed" and "actually ran" is visible even when every id still
    resolves."""

    def fn(node_ids: Sequence[str]) -> int:
        if not node_ids:
            return 0
        collected = _collect_python_and_rust_ids(root)
        if collected.is_err:
            _log.warning(
                "ticket: capture collection failed (%s) -- treating all %d "
                "evidence id(s) as not passing",
                collected.danger_err,
                len(node_ids),
            )
            return 0
        python_ids, rust_ids, runners = collected.danger_ok
        passing = _verify_ids_passing(root, node_ids, python_ids, rust_ids, runners)
        return len(passing)

    return fn


# frob:ticket T-0458
# frob:ticket T-0754
# frob:tests tests/test_tickets_evidence_cli.py::TestDoneReportCli.test_cli_composes_and_writes  # noqa: E501
def _done_report(root: Path, cfg: AppConfig) -> None:
    """`frob ticket done-report <id> (--why TEXT | --why-file PATH | -)`:
    resolve the narrative why, then call `frob.tickets.set_done_report` --
    the ONLY thing this command does is supply `why`; the Changed and
    Evidence sections are composed entirely inside `set_done_report` from
    git and the ticket's own recorded evidence, never parsed/typed here
    (T-0458).

    T-0754: also supplies `run_tests`/`check_gates` (`_run_tests_count_fn`/
    `_check_gates_summary_fn`) so `set_done_report` captures a real
    `### Captured claims` section -- a test count from actually running
    the ticket's own evidence and a gate-state summary from a fresh `frob
    check --ticket`, neither typed by the agent -- instead of leaving the
    Done report's test/gate claims as unverified free prose."""
    from frob.tickets import set_done_report

    if cfg.ticket_id is None:
        _log.error("frob ticket done-report requires <id>")
        sys.exit(1)

    why = _resolve_done_report_why(cfg)
    if why is None:
        _log.error(
            "frob ticket done-report requires --why TEXT, --why-file PATH, "
            "or a narrative piped via stdin"
        )
        sys.exit(1)

    result = set_done_report(
        root,
        cfg.ticket_id,
        why=why,
        base_ref=cfg.ticket_base_ref,
        run_tests=_run_tests_count_fn(root),
        check_gates=_check_gates_summary_fn(root, cfg.ticket_id),
        check_gate_findings=_check_gate_findings_fn(root, cfg.ticket_id),
    )
    if result.is_err:
        _log.error("done-report failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: Done report written (%d evidence id(s) rendered)",
        cfg.ticket_id,
        len(ticket.evidence),
    )


# frob:ticket T-0737
def _resolve_scope_reason(cfg: AppConfig) -> str | None:
    """Resolve `frob ticket scope`'s `--reason`: `--reason-file` wins if
    given (read verbatim -- T-0737, same rationale as `_resolve_new_body`),
    else the inline `--reason` string. Exits 1 if both are given; returns
    `None` if neither is given (the caller reports the "one is required"
    error, matching `_resolve_done_report_why`'s shape)."""
    if cfg.ticket_scope_reason_file is not None and cfg.ticket_scope_reason:
        _log.error(
            "frob ticket scope: --reason and --reason-file are mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_scope_reason_file is not None:
        try:
            return cfg.ticket_scope_reason_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket scope: could not read --reason-file %s: %s",
                cfg.ticket_scope_reason_file,
                exc,
            )
            sys.exit(1)
    return cfg.ticket_scope_reason


# frob:ticket T-0455
# frob:ticket T-0737
# frob:tests tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_free_path
# frob:tests tests/test_tickets_scope_mutation.py::TestScopeCli.test_cli_add_leased_path_exits_nonzero  # noqa: E501
def _scope(root: Path, cfg: AppConfig) -> None:
    """`frob ticket scope <id> --add GLOB... --remove GLOB... (--reason
    TEXT | --reason-file PATH)`: the ONLY thing this command does is
    resolve the reason (`_resolve_scope_reason`, T-0737) and forward to
    `frob.tickets.mutate_scope` -- all lease-conflict/evidence-orphan
    validation lives there (T-0455), never re-derived here."""
    from frob.tickets import mutate_scope

    if cfg.ticket_id is None:
        _log.error("frob ticket scope requires <id>")
        sys.exit(1)
    if not cfg.ticket_scope_add and not cfg.ticket_scope_remove:
        _log.error("frob ticket scope requires --add and/or --remove GLOB")
        sys.exit(1)

    reason = _resolve_scope_reason(cfg)
    if not reason:
        _log.error("frob ticket scope requires --reason TEXT or --reason-file PATH")
        sys.exit(1)

    result = mutate_scope(
        root,
        cfg.ticket_id,
        add=cfg.ticket_scope_add,
        remove=cfg.ticket_scope_remove,
        reason=reason,
    )
    if result.is_err:
        _log.error("scope change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: scope now %s (+%d/-%d this change)",
        cfg.ticket_id,
        list(ticket.scope),
        len(cfg.ticket_scope_add),
        len(cfg.ticket_scope_remove),
    )


# frob:ticket T-0411
def _priority(root: Path, cfg: AppConfig) -> None:
    """`frob ticket priority <id> <level>`: the ONLY thing this command does
    is forward to `frob.tickets.set_priority` -- no validation is re-derived
    here (T-0411, same pattern as `_scope`/T-0455)."""
    from frob.tickets import Priority, set_priority

    if cfg.ticket_id is None or cfg.ticket_priority_level is None:
        _log.error("frob ticket priority requires <id> <level>")
        sys.exit(1)

    result = set_priority(root, cfg.ticket_id, Priority(cfg.ticket_priority_level))
    if result.is_err:
        _log.error("priority change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: priority now %s", cfg.ticket_id, ticket.priority.value)


# frob:ticket T-0834
def _kind(root: Path, cfg: AppConfig) -> None:
    """`frob ticket kind <id> <kind>`: the ONLY thing this command does is
    forward to `frob.tickets.set_kind` -- no validation is re-derived here
    (T-0834, same pattern as `_priority`/T-0411). `kind` is validated
    strictly against the real `TicketKind` enum inside `TicketKind(...)`;
    an unknown value raises `ValueError`, reported and exited the same way
    an unresolvable ticket id is."""
    from frob.tickets import TicketKind, set_kind

    if cfg.ticket_id is None or cfg.ticket_kind_value is None:
        _log.error("frob ticket kind requires <id> <kind>")
        sys.exit(1)

    try:
        kind = TicketKind(cfg.ticket_kind_value)
    except ValueError:
        _log.error(
            "frob ticket kind: %r is not a valid kind (choose from %s)",
            cfg.ticket_kind_value,
            sorted(k.value for k in TicketKind),
        )
        sys.exit(1)

    result = set_kind(root, cfg.ticket_id, kind)
    if result.is_err:
        _log.error("kind change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: kind now %s", cfg.ticket_id, ticket.kind.value)


# frob:ticket T-0454
def _component(root: Path, cfg: AppConfig) -> None:
    """`frob ticket component <id> <name>`: forward to
    `frob.tickets.set_component` -- `name == "none"` clears the field back
    to uncategorized (T-0454, same pattern as `_priority`/`_scope`)."""
    from frob.tickets import set_component

    if cfg.ticket_id is None or cfg.ticket_component is None:
        _log.error("frob ticket component requires <id> <name>")
        sys.exit(1)

    value = None if cfg.ticket_component == "none" else cfg.ticket_component
    result = set_component(root, cfg.ticket_id, value)
    if result.is_err:
        _log.error("component change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: component now %s", cfg.ticket_id, ticket.component)


# frob:ticket T-0454
def _label(root: Path, cfg: AppConfig) -> None:
    """`frob ticket label <id> --add TAG... --remove TAG...`: forward to
    `frob.tickets.mutate_labels` -- all validation lives there (T-0454, same
    "this command does nothing but forward" pattern as `_scope`)."""
    from frob.tickets import mutate_labels

    if cfg.ticket_id is None:
        _log.error("frob ticket label requires <id>")
        sys.exit(1)
    if not cfg.ticket_label_add and not cfg.ticket_label_remove:
        _log.error("frob ticket label requires --add and/or --remove TAG")
        sys.exit(1)

    result = mutate_labels(
        root,
        cfg.ticket_id,
        add=cfg.ticket_label_add,
        remove=cfg.ticket_label_remove,
    )
    if result.is_err:
        _log.error("label change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: labels now %s (+%d/-%d this change)",
        cfg.ticket_id,
        list(ticket.labels),
        len(cfg.ticket_label_add),
        len(cfg.ticket_label_remove),
    )


# frob:ticket T-0454
def _board(root: Path, cfg: AppConfig) -> None:
    """`frob ticket board [--component NAME] [--label TAG] [--json]`:
    render `frob.tickets.board_view`'s fixed state columns, each
    priority-then-age ordered (T-0454)."""
    from frob.tickets import board_view, load_active

    result = load_active(root)
    if result.is_err:
        _log.error("ticket board failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    columns = board_view(
        queue, component=cfg.ticket_board_component, label=cfg.ticket_board_label
    )

    if cfg.ticket_json:
        import json

        payload = [
            {
                "state": col.state.value,
                "tickets": [t.model_dump(mode="json") for t in col.tickets],
            }
            for col in columns
        ]
        _log.info(json.dumps(payload, indent=2))
        return

    color = _stdout_color()
    for col in columns:
        _log.info("%s (%d)", style_state(col.state.value, color), len(col.tickets))
        if not col.tickets:
            continue
        for t in col.tickets:
            _log.info(
                "  %s  %s  (%s, %s)",
                style_ticket_id(t.id, color),
                t.title,
                t.priority.value,
                t.component or "uncategorized",
            )


# frob:ticket T-0454
def _epic(root: Path, cfg: AppConfig) -> None:
    """`frob ticket epic <id> [--json]`: render `frob.tickets.epic_rollup`'s
    subtree summary (T-0454)."""
    from frob.tickets import epic_rollup, load_active

    if cfg.ticket_id is None:
        _log.error("frob ticket epic requires <id>")
        sys.exit(1)
    result = load_active(root)
    if result.is_err:
        _log.error("ticket epic failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    rollup_result = epic_rollup(queue, cfg.ticket_id)
    if rollup_result.is_err:
        _log.error("ticket epic failed: %s", rollup_result.danger_err)
        sys.exit(1)
    rollup = rollup_result.danger_ok

    if cfg.ticket_json:
        import json

        payload = {
            "epic": rollup.epic.model_dump(mode="json"),
            "descendants": [t.model_dump(mode="json") for t in rollup.descendants],
            "done": rollup.done,
            "total": rollup.total,
            "percent_complete": rollup.percent_complete,
            "blocked_leaves": list(rollup.blocked_leaves),
        }
        _log.info(json.dumps(payload, indent=2))
        return

    color = _stdout_color()
    _log.info(
        "%s  %s  -- %d/%d done (%.0f%%)",
        style_ticket_id(rollup.epic.id, color),
        rollup.epic.title,
        rollup.done,
        rollup.total,
        rollup.percent_complete,
    )
    for t in rollup.descendants:
        _log.info(
            "  %s  [%s]  %s",
            style_ticket_id(t.id, color),
            style_state(t.state.value, color),
            t.title,
        )
    if rollup.blocked_leaves:
        _log.info("blocked leaves: %s", list(rollup.blocked_leaves))


# frob:ticket T-0568
def _brief(root: Path, cfg: AppConfig) -> None:
    """`frob ticket brief <id>` (T-0568): print `frob.tickets.brief_ticket`'s
    full mission briefing text -- the entire point is a single command a
    coordinator can paste into a dispatch prompt instead of hand-typing
    the same ~400 words of playbook/scope/verify boilerplate every time."""
    from frob.tickets import brief_ticket

    if cfg.ticket_id is None:
        _log.error("frob ticket brief requires <id>")
        sys.exit(1)
    result = brief_ticket(root, cfg.ticket_id)
    if result.is_err:
        _log.error("ticket brief failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s", result.danger_ok)


# frob:ticket T-0398
def _collect_python_and_rust_ids(root: Path):  # noqa: ANN201
    """`(python_ids, rust_ids, runners)` -- the same union-collection dance
    `_apply_evidence` always did (T-0301), factored out so both evidence
    recording (D-01 pass-check) and `frob ticket land`'s post-merge
    re-verification (D-05) share one implementation. Returns `Err` only on
    a python collection failure (rust degrades to a WARNING + empty set,
    matching the existing resilience posture); `runners` is `()` if
    `load_runners` itself fails."""
    from frob.testing import collect_python_tests, collect_rust_tests, load_runners

    collected = collect_python_tests(root)
    if collected.is_err:
        return collected

    python_ids = frozenset(collected.danger_ok.node_ids)
    rust_ids: frozenset[str] = frozenset()

    runners = load_runners(root)
    runner_specs = runners.danger_ok if runners.is_ok else ()
    if any(spec.language == "rust" for spec in runner_specs):
        rust_collected = collect_rust_tests(root)
        if rust_collected.is_err:
            _log.warning(
                "ticket evidence: rust collection failed (%s); validating "
                "against pytest ids only for this call",
                rust_collected.danger_err,
            )
        else:
            rust_ids = frozenset(rust_collected.danger_ok.node_ids)

    from typani.result import Ok

    return Ok((python_ids, rust_ids, runner_specs))


# frob:ticket T-0398
def _verify_ids_passing(
    root: Path,
    node_ids,  # noqa: ANN001
    python_collected: frozenset[str],
    rust_collected: frozenset[str],
    runners,  # noqa: ANN001
) -> frozenset[str]:
    """D-01 CLI wiring: actually RUN `node_ids` (bucketed by which
    collected set each id resolves against, python vs rust) and return the
    subset that passed -- the piece that makes `frob ticket evidence`/
    `close`/`land` mean "the work was actually tested," not just "a test
    with this name exists."

    Each language bucket is run as its OWN `run_selected` call, not one
    combined invocation, for two reasons: (1) a combined run's single exit
    code cannot tell you WHICH of several ids failed, so a batch mixing a
    red and a green id would have to reject both -- overly strict for no
    reason; per-language buckets are the coarsest split that still lets
    genuinely-independent ids pass independently. (2) an infra failure in
    one language (e.g. no PyO3 env for rust) must not silently swallow a
    python id's real, successful verification -- each bucket's own
    Err/failure is logged and only THAT bucket's ids are withheld from the
    returned passing set, never the whole call. An id that resolves
    against neither collected set is simply absent from the result (it
    already fails resolution elsewhere; this function only concerns
    itself with ids that at least exist)."""
    from frob.tickets._models import matches_collected

    passing: set[str] = set()
    buckets = {
        "python": tuple(n for n in node_ids if matches_collected(n, python_collected)),
        "rust": tuple(n for n in node_ids if matches_collected(n, rust_collected)),
    }
    for language, items in buckets.items():
        if items:
            passing.update(_verify_one_bucket_passing(root, language, items, runners))
    return frozenset(passing)


# frob:ticket T-0398
def _verify_one_bucket_passing(
    root: Path,
    language: str,
    items: tuple[str, ...],
    runners,  # noqa: ANN001
) -> frozenset[str]:
    """One language bucket of `_verify_ids_passing`'s work: run `items`
    via `run_selected` and return the subset (all-or-nothing per bucket,
    see `_verify_ids_passing`'s docstring) that passed. Falls back to a
    direct `pytest <ids>` invocation for python when no `[[test.runner]]`
    is declared at all -- `frob.toml` is optional, so a repo that never
    configured one must not fall straight to "not passing" (a false-
    positive trap this fix was explicitly warned against)."""
    from frob.testing import SelectionReport, TestingError, run_selected

    selection = SelectionReport(
        touched=(),
        selected={language: items},
        ripple=(),
        unbound=(),
        fallback="evidence-verify",
    )
    run = run_selected(selection, runners, root)
    if run.is_ok and run.danger_ok.ok:
        return frozenset(items)
    if run.is_err and language == "python" and run.danger_err == TestingError.NoRunner:
        if _run_pytest_directly(root, items):
            return frozenset(items)
        _log.warning(
            "ticket evidence: direct pytest verification FAILED for %s", list(items)
        )
        return frozenset()
    _log.warning(
        "ticket evidence: %s verification %s for %s",
        language,
        f"run failed to execute ({run.danger_err})" if run.is_err else "run FAILED",
        list(items),
    )
    return frozenset()


# frob:ticket T-0398
def _run_pytest_directly(root: Path, node_ids) -> bool:  # noqa: ANN001
    """`uv run pytest <node_ids> -q -o addopts=` in `root`, exit 0 == pass
    -- the no-`[[test.runner]]`-declared fallback `_verify_ids_passing`
    uses so D-01 verification works even in a repo that never configured
    `frob.toml`'s test-runner registry (the same posture
    `collect_python_tests` already takes for collection)."""
    from frob.gitio import run_argv

    argv = ("uv", "run", "pytest", *node_ids, "-q", "-o", "addopts=")
    spawned = run_argv(argv, cwd=root, timeout_s=300.0)
    if spawned.is_err:
        _log.warning("ticket evidence: direct pytest failed to spawn in %s", root)
        return False
    return spawned.danger_ok.returncode == 0


# frob:ticket T-0106
# frob:ticket T-0398
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_evidence(
    root: Path,
    ticket_id: str,
    node_ids: list[str],
    accepts: list[int] | None = None,
):
    """Collect pytest node ids, validate `node_ids` against them AND
    actually run them (D-01: `passed`) via `frob.tickets.add_evidence`
    (resolvable-id + passing + dedupe semantics, wholesale batch rejection
    on any unresolvable OR non-passing id), and append the resolvable
    passing ones to `ticket_id`'s structured evidence list. Shared by
    `frob ticket evidence`, `frob ticket new --evidence`, and `frob ticket
    close --evidence` so all three routes go through identical validation
    -- never through an ad hoc, unvalidated write. Returns the
    `add_evidence` Result unchanged so callers (e.g. `_close`) can refuse
    to transition state on failure.

    `accepts` (T-0572) threads straight through to `add_evidence`'s own
    `accepts`: 0-based `ticket.acceptance` indices `node_ids` also bind to,
    in the same write. `None`/empty binds nothing (the pre-T-0572 default).

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
    guidance elsewhere in this module).

    T-0398: this is the CLI's STRICT default -- `passed` is always
    computed and always passed to `add_evidence`, so a red/errored/
    skipped evidence test rejects the whole batch (`EvidenceNotPassing`)
    through the real `frob ticket evidence`/`close` commands, not just the
    library function a caller could otherwise bypass by never supplying
    `passed`.

    T-0492: `node_ids` is normalized (`normalize_evidence_separator`, the
    SAME dot-to-`::` rewrite `add_evidence`'s own `_validate_evidence_list`
    applies, T-0293) BEFORE it is handed to `_verify_ids_passing` here --
    not after. `_verify_ids_passing` buckets ids via `matches_collected`
    against `python_ids`/`rust_ids`, which only ever contain pytest's
    native `::`-form node ids; a raw dot-form id (`path::Class.method`,
    the canonical spelling this module's own docs teach) never matches
    either bucket, so its "did it pass" check silently runs on an empty
    selection and the id ends up absent from `passing` -- rejected
    downstream as `EvidenceNotPassing` even though the test genuinely
    passed. Passing the SAME normalized list into both the passing-check
    and `add_evidence` keeps the two normalization paths from silently
    diverging again."""
    from frob.tickets import add_evidence, normalize_evidence_separator

    collected = _collect_python_and_rust_ids(root)
    if collected.is_err:
        _log.error(
            "ticket evidence: pytest collection failed: %s", collected.danger_err
        )
        return collected
    python_ids, rust_ids, runners = collected.danger_ok
    collected_ids = python_ids | rust_ids

    normalized_ids = [normalize_evidence_separator(n) for n in node_ids]
    passing = _verify_ids_passing(root, normalized_ids, python_ids, rust_ids, runners)

    result = add_evidence(
        root, ticket_id, normalized_ids, collected_ids, passed=passing, accepts=accepts
    )
    _log_evidence_result(ticket_id, result)
    return result


def _log_evidence_result(ticket_id: str, result) -> None:  # noqa: ANN001
    """Log `add_evidence`'s outcome: the failure reason + remedy, or the
    ticket's resulting evidence id count."""
    if result.is_err:
        _log.error(
            "ticket evidence failed: %s (the collection cache self-refreshes "
            "on the next `frob test` / `frob check` run; if it still does "
            "not resolve, delete .frob/pytest-collect.json (or "
            ".frob/cargo-collect.json for rust) to force a rebuild, or fix "
            "the id)",
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
# frob:ticket T-0796
# frob:tests tests/test_tickets_evidence_cli.py
def _apply_cmd_evidence(
    root: Path, ticket_id: str, command: str, accepts: Sequence[int] | None = None
):
    """Run `command` via `frob.tickets.add_cmd_evidence` and append its
    exit-status/digest entry to `ticket_id`'s evidence list -- the
    docs/design-kind non-pytest evidence channel (T-0215). Returns the
    `add_cmd_evidence` Result unchanged so callers (`_close`, `_evidence`)
    can refuse to transition state on failure, the same contract
    `_apply_evidence` gives pytest-node-id evidence.

    `accepts` (T-0796) is threaded straight through to `add_cmd_evidence`
    so `--accepts` binds cmd evidence onto the named acceptance criteria
    exactly like it already does for pytest-node evidence via
    `_apply_evidence` -- before this, both call sites below dropped
    `cfg.ticket_accepts` for the cmd-evidence path, so a docs-kind ticket
    closed with `--evidence-cmd` + `--accepts` silently ended up UNBOUND."""
    from frob.tickets import add_cmd_evidence

    result = add_cmd_evidence(root, ticket_id, command, accepts)
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
# frob:ticket T-0810
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
