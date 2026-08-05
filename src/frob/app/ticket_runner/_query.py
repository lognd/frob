"""frob.app.ticket_runner._query -- the `list`/`show`/`doable`/`migrate`/
`renumber` read-path command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: this file's \
# exclusivity-vocabulary hit is source-level design-rationale/ scope-cut prose (a \
# docstring or comment describing already-implemented internal behavior, verifiable by \
# reading the code it annotates) rather than a separate cross-module contract needing \
# its own tracked invariant; disposed as a calibration batch, not claim-by-claim -- \
# carried from the pre-T-1089-split monolith's identical file-level waiver \
# (frob.app.ticket_runner/__init__.py)"

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from frob.app._style import style_state, style_ticket_id
from frob.app.config import AppConfig
from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.tickets import Ticket, TicketQueue

_log = get_logger("frob.app.ticket_runner")


def _filter_by_state(tickets, state):
    """Tickets whose state equals `state` (extracted so `_list` stays a flat
    sequence of independent steps, not a nested-loop join)."""
    return [t for t in tickets if t.state == state]


# frob:ticket T-1528
# frob:ticket T-0716
# frob:ticket T-1530
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

    from frob.app.ticket_runner import _stdout_color

    color = _stdout_color()
    if not tickets:
        _log.info("no tickets")
        _log.info("%s", _summary_footer(root, queue, color))
        if cfg.ticket_stats:
            _log.info("%s", _stats_line(root, queue))
        return
    for t in tickets:
        _log.info(
            "%s  [%s]  %s  (%s)",
            style_ticket_id(t.id, color),
            style_state(display_state(t, root), color),
            t.title,
            t.kind.value,
        )
    _log.info("%s", _summary_footer(root, queue, color))
    if cfg.ticket_stats:
        _log.info("%s", _stats_line(root, queue))


# frob:ticket T-1528
# frob:ticket T-1530
def _summary_footer(root: Path, queue, color: bool = False) -> str:  # noqa: ANN001
    """One-line per-state census of the ACTIVE queue (T-1528) -- the
    always-on `frob ticket list` footer that replaces the
    `list | grep queued | wc -l` shell idiom. Computed from the queue the
    list just loaded plus the live lease overlay.

    T-1530: counts `display_state(t, root)`'s base state (the part before
    any `@worktree` decoration), NOT the raw ledger state, so the census
    always agrees with the rows rendered above it -- a leased-but-ledger-
    queued ticket displays `[in-progress@...]` and must count as
    in-progress here too. State names are styled through the same
    `style_state` helper the rows use (no-op when `color` is False)."""
    from collections import Counter

    from frob.tickets import TicketState, display_state

    counts = Counter(
        display_state(t, root).split("@")[0] for t in queue.tickets.values()
    )
    order = (
        TicketState.QUEUED,
        TicketState.PLANNED,
        TicketState.IN_PROGRESS,
        TicketState.BLOCKED,
        TicketState.DONE,
        TicketState.DROPPED,
    )
    parts = [
        f"{counts[s.value]} {style_state(s.value, color)}"
        for s in order
        if counts[s.value]
    ]
    total = sum(counts.values())
    body = ", ".join(parts) if parts else "empty"
    return f"summary: {total} active ({body})"


# frob:ticket T-1528
def _stats_line(root: Path, queue) -> str:  # noqa: ANN001
    """`frob ticket list --stats` second footer line (T-1528): trailing
    filed/landed/net per-day rates, median cycle time, and the naive
    burn-down ETA -- all straight off `ticket_flow`'s existing T-1100
    report, no new mining."""
    from frob.tickets import ticket_flow

    report = ticket_flow(root, queue)
    trailing = report.rows[-3:]
    days = len(trailing) or 1
    filed = sum(r.filed for r in trailing) / days
    landed = sum(r.landed for r in trailing) / days
    cycle = (
        f"{report.median_cycle_days:.1f}d"
        if report.median_cycle_days is not None
        else "n/a"
    )
    eta = report.eta_days
    eta_text = f"~{eta:.0f}d" if eta is not None else "not shrinking"
    return (
        f"stats: open {report.open_count} | trailing-3d filed {filed:.1f}/d, "
        f"landed {landed:.1f}/d, net {report.trailing_net_rate:+.1f}/d | "
        f"median cycle {cycle} | backlog ETA {eta_text}"
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

    from frob.app.ticket_runner import _stdout_color

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
    if not ticket.acceptance and not ticket.acceptance_amendments:
        return ""
    lines = ["\nacceptance:"] if ticket.acceptance else []
    for i, item in enumerate(ticket.acceptance):
        status = f"bound({list(item.evidence)})" if item.evidence else "UNBOUND"
        lines.append(f"  [{i}] {status}: {item.text}")
    lines.extend(_render_acceptance_amendments(ticket))
    return "\n".join(lines)


# frob:ticket T-1422
def _render_acceptance_amendments(ticket) -> list[str]:  # noqa: ANN001
    """The `\\nacceptance_amendments: ...` lines `frob ticket show` appends
    after the acceptance list (T-1422) -- never buried: every `--amend`/
    `--remove` this ticket's acceptance has gone through, in order, with
    its full reason. Empty list (no extra lines) when the ticket has no
    recorded amendments, matching `_render_acceptance`'s own "nothing to
    add" posture."""
    if not ticket.acceptance_amendments:
        return []
    lines = ["\nacceptance_amendments:"]
    for entry in ticket.acceptance_amendments:
        if entry.op.value == "replace":
            change = f"{entry.old_text!r} -> {entry.new_text!r}"
        else:
            change = f"removed {entry.old_text!r}"
        lines.append(
            f"  [{entry.index}] {entry.op.value}: {change} "
            f"(reason: {entry.reason}; {entry.actor}, {entry.at})"
        )
    return lines


# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_doable_tickets_json_daemon_matches_in_process kind="unit"  # noqa: E501
def _try_doable_via_daemon(root: Path, cfg: AppConfig) -> bool:
    """T-1128: for a plain `frob ticket doable --json` (no `--show-blocked`,
    `--ignore-lease`, or `--sprint` -- the RPC's own fixed-arity `frob.
    serve._tools.frob_doable_tickets(root)` contract has no parameter for
    any of those), try the daemon's RPC via `frob.app._daemon_proxy.query`
    before doing any local queue load/filter. Returns `True` on a daemon
    hit (already rendered); `False` falls through to the in-process path
    unchanged, same contract `_try_affects_via_daemon` (T-1106)
    established. The RPC now returns each ticket's full `model_dump(mode=
    'json')` (T-1128), field-for-field identical to this CLI's own
    `--json` per-row shape."""
    if (
        not cfg.ticket_json
        or cfg.ticket_show_blocked
        or cfg.ticket_ignore_lease
        or cfg.ticket_doable_sprint is not None
    ):
        return False
    from frob.app._daemon_proxy import query

    proxied = query(root, "frob_doable_tickets", {})
    if proxied.is_err:
        return False
    import json

    _log.info(json.dumps(proxied.danger_ok, indent=2))
    return True


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
    if _try_doable_via_daemon(root, cfg):
        return

    from frob.tickets import (
        doable,
        has_live_lease,
        load_queue,
        scope_breadth_context,
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

    # frob:ticket T-0715
    # `frob ticket doable --sprint LABEL` restricts the queue to one
    # sprint's commitment -- a plain post-filter, since `doable()` itself
    # stays sprint-agnostic (the T-0453 lease/breadth machinery it already
    # threads through has nothing to do with sprint membership).
    if cfg.ticket_doable_sprint is not None:
        tickets = tuple(t for t in tickets if t.sprint == cfg.ticket_doable_sprint)

    if cfg.ticket_json:
        import json

        _log.info(json.dumps([t.model_dump(mode="json") for t in tickets], indent=2))
        return

    _render_active_leases(queue)
    _render_scope_breadth_summary(root, queue, breadth=breadth)

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
    # frob:ticket T-0972
    # PERF001: test membership against a set of ids, not the `in_flight`
    # list itself, on every iteration of the comprehension below.
    in_flight_ids = {t.id for t in in_flight}
    dispatchable = [t for t in tickets if t.id not in in_flight_ids]

    ordered, alarm_by_id = _order_dispatchable_with_alarms(dispatchable, root)
    _render_doable_dispatchable(ordered, alarm_by_id, queue, cfg)
    _render_doable_in_flight(in_flight)


# frob:ticket T-0976
def _order_dispatchable_with_alarms(
    dispatchable: list, root: Path
) -> tuple[list, dict]:
    """Sort `dispatchable` so any CRITICAL/HIGH row that has sat past its
    `undispatched_stale` threshold sorts first, and return that ordering
    alongside a `ticket-id -> (elapsed, threshold)` map for the alarms
    found -- shared state the flat and `--by-parent` renders both need."""
    from frob.tickets import undispatched_stale

    alarms = undispatched_stale(dispatchable, root)
    alarmed_ids = {t.id for t, _elapsed, _threshold in alarms}
    ordered = [t for t in dispatchable if t.id in alarmed_ids] + [
        t for t in dispatchable if t.id not in alarmed_ids
    ]
    alarm_by_id = {t.id: (elapsed, threshold) for t, elapsed, threshold in alarms}
    return ordered, alarm_by_id


# frob:ticket T-0976
def _doable_row(t: "Ticket", alarm_by_id: dict, color: bool) -> str:
    """One doable-list line for `t`, including its UNDISPATCHED alarm (if
    any) -- shared by the flat and `--by-parent` grouped renders (T-0715)
    so the two stay in sync instead of duplicating the format."""
    row = "%s  %s  (%s)  priority=%s" % (
        style_ticket_id(t.id, color),
        t.title,
        t.kind.value,
        t.priority.value,
    )
    if t.id in alarm_by_id:
        elapsed, threshold = alarm_by_id[t.id]
        row += "  [UNDISPATCHED %.0fh > %.0fh threshold]" % (elapsed, threshold)
    return row


# frob:ticket T-0976
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping.test_parent_id_not_in_queue_falls_back_to_no_parent_bucket  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping.test_parent_id_present_in_queue_uses_its_title  # noqa: E501
def _render_doable_dispatchable(
    ordered: list, alarm_by_id: dict, queue: "TicketQueue", cfg: AppConfig
) -> None:
    """Print the dispatchable section of `frob ticket doable`: a flat
    priority/age/alarm-ordered list, or (`--by-parent`, T-0715) the same
    rows grouped by `parent` so a story's remaining leaves display
    together instead of scattered across one flat list."""
    from frob.app.ticket_runner import _stdout_color

    color = _stdout_color()

    if not cfg.ticket_doable_by_parent:
        for t in ordered:
            _log.info(_doable_row(t, alarm_by_id, color))
        return

    # A row with no `parent` (or a parent id `queue` cannot resolve) falls
    # into its own "no parent" bucket rather than being dropped. Group
    # order follows first appearance in the already priority/age/alarm-
    # ordered `ordered` list, so the highest-priority group still leads.
    groups: dict[str | None, list["Ticket"]] = {}
    for t in ordered:
        groups.setdefault(t.parent, []).append(t)
    for parent_id, rows in groups.items():
        header = (
            queue.tickets[parent_id].title
            if parent_id is not None and parent_id in queue.tickets
            else "(no parent)"
        )
        _log.info(
            "%s:",
            f"{style_ticket_id(parent_id, color)} {header}"
            if parent_id is not None
            else header,
        )
        for t in rows:
            _log.info("  %s", _doable_row(t, alarm_by_id, color))


# frob:ticket T-0976
def _render_doable_in_flight(in_flight: list) -> None:
    """Print the "In-flight (leased, already being worked)" section of
    `frob ticket doable`, if any dispatchable-but-leased rows exist."""
    if not in_flight:
        return
    from frob.app.ticket_runner import _stdout_color

    color = _stdout_color()
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
    from frob.app.ticket_runner import _stdout_color

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
    the full per-ticket detail `frob check`'s TICK009 (T-0714) renders one
    line per finding for. `frob ticket doable` itself only shows a single
    count line (`_render_scope_breadth_summary`) -- this function is the
    shared detail computation both consume. Pass a precomputed `breadth`
    (`scope_breadth_context(root)`) so the breadth walk runs once for the
    whole listing, not once per ticket."""
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


# frob:ticket T-0714
def _render_scope_breadth_summary(
    root: Path,
    queue: "TicketQueue",
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> None:
    """`frob ticket doable`'s scope-breadth diagnostic (T-0714): a single
    summary line naming how many over-broad-scope nudges are outstanding
    across the queue, instead of one `WARNING:` line per nudge per
    invocation (the pre-T-0714 behavior, which flooded every `doable` call
    with a repeated wall of per-ticket warnings -- see TICK009's
    `docs/modules/gates.md` entry). The per-ticket detail moved to `frob
    check`'s TICK009 gate, which reports each one exactly once with
    remediation; doable's job is a clean ordered queue listing, not a
    diagnostic dump. Prints nothing when the count is zero."""
    warnings = _active_large_glob_warnings(root, queue, breadth=breadth)
    if not warnings:
        return
    _log.info(
        "%d scope-breadth nudge(s) outstanding across the queue -- "
        "see 'frob check --only tickets' (TICK009) for detail",
        len(warnings),
    )


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
    from frob.app.ticket_runner import _stdout_color

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
