"""frob.app.ticket_runner._query -- the `list`/`show`/`doable`/`migrate`/
`renumber` read-path command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""

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
# frob:ticket T-1733
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
        "%s  [%s]  %s  (%s)\nblocked_by=%s scope=%s%s%s%s%s\n\n%s",
        style_ticket_id(ticket.id, color),
        style_state(display_state(ticket, root), color),
        ticket.title,
        ticket.kind.value,
        list(ticket.blocked_by),
        list(ticket.scope),
        _render_implicit_scope(ticket),
        _render_designated_repro(ticket),
        _render_acceptance(ticket),
        _render_evidence_changes(ticket),
        ticket.body,
    )


# frob:ticket T-1855
def _render_implicit_scope(ticket) -> str:  # noqa: ANN001
    """The `\\nimplicit_scope: [...]` line `frob ticket show` appends
    after `scope=` (T-1855) -- the FEATURE-kind CLI-wiring files
    (`CLI_WIRING_FILES`, T-0446/T-1848) this ticket effectively holds
    that are NOT part of its own declared `scope` list. Today the
    declared list is all `frob ticket show` prints, so an agent (or a
    coordinator running `scope --remove`) cannot see that the ticket
    holds more than it declared -- this is the disclosure half of the
    T-1848 incident writeup (T-1855 item 2). Empty string (no extra line)
    for a non-FEATURE ticket or a FEATURE ticket whose declared scope
    already covers every CLI-wiring file, matching every sibling
    `_render_*` helper's "nothing to add" posture."""
    from frob.tickets._models import CLI_WIRING_FILES, TicketKind, scope_matches

    if ticket.kind is not TicketKind.FEATURE:
        return ""
    implicit = sorted(
        path
        for path in CLI_WIRING_FILES
        if not scope_matches(path, ticket.scope, ticket_id=ticket.id)
    )
    if not implicit:
        return ""
    return (
        f"\nimplicit_scope: {implicit}  "
        "(FEATURE-kind CLI-wiring grant, T-0446/T-1848 -- not in declared "
        "scope; 'scope --remove' cannot free these)"
    )


# frob:ticket T-1670
def _render_designated_repro(ticket) -> str:  # noqa: ANN001
    """The `\\ndesignated_repro_test: <id>` line `frob ticket show` appends
    after `scope=` (T-1670) whenever a ticket has an explicit BUG002 repro
    designation -- surfaces which id currently wins over the positional-
    first-match default, so an agent binding a second/third evidence id
    can see at a glance whether it will silently become the new repro
    (it will not, once a designation exists) rather than discovering the
    ordering rule only at land time. Empty string (no extra line) when no
    designation is set, matching pre-T-1670 output exactly."""
    if ticket.designated_repro_test is None:
        return ""
    return f"\ndesignated_repro_test: {ticket.designated_repro_test}"


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


# frob:ticket T-1733
def _render_evidence_changes(ticket) -> str:  # noqa: ANN001
    """T-1733 requirement 4: the `\\nevidence_changes: ...` lines `frob
    ticket show` appends after the acceptance block -- the SAME "never
    buried, always shown with its reason" posture `_render_acceptance_
    amendments` already gives acceptance criteria, applied to evidence.
    A reviewer reading `frob ticket show` sees what was rebound and why,
    not just the final evidence list a silent unbind would otherwise
    leave looking perfectly fine. Empty string (no extra lines) when the
    ticket's evidence was never rebound, matching every sibling
    `_render_*` helper's "nothing to add" posture."""
    if not ticket.evidence_changes:
        return ""
    lines = ["\nevidence_changes:"]
    for entry in ticket.evidence_changes:
        lines.append(
            f"  {entry.old_node!r} -> {entry.new_node!r} "
            f"(reason: {entry.reason}; {entry.actor}, {entry.at})"
        )
    return "\n".join(lines)


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
# frob:ticket T-1822
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
    tickets = doable(
        queue,
        root,
        ignore_lease=cfg.ticket_ignore_lease,
        breadth=breadth,
        show_anchors=cfg.ticket_doable_show_anchors,
    )

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
    landed_ids = _render_already_landed_markers(root, queue, breadth=breadth)

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
    _render_doable_dispatchable(ordered, alarm_by_id, queue, cfg, landed_ids=landed_ids)
    _render_doable_in_flight(in_flight, _stale_lease_reasons(root))


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
# frob:ticket T-1822
# frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestDoableRowLandedMarker.test_flagged_id_gets_inline_marker  # noqa: E501
# frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestDoableRowLandedMarker.test_unflagged_id_gets_no_marker  # noqa: E501
def _doable_row(
    t: "Ticket",
    alarm_by_id: dict,
    color: bool,
    *,
    landed_ids: frozenset[str] = frozenset(),
) -> str:
    """One doable-list line for `t`, including its UNDISPATCHED alarm (if
    any) -- shared by the flat and `--by-parent` grouped renders (T-0715)
    so the two stay in sync instead of duplicating the format. T-1822:
    also appends an ALREADY-LANDED marker when `t.id` is in `landed_ids`
    (`_render_already_landed_markers`'s return value) -- the inline,
    per-row half of that wiring, alongside the summary line it prints
    once per `doable` call."""
    row = "%s  %s  (%s)  priority=%s" % (
        style_ticket_id(t.id, color),
        t.title,
        t.kind.value,
        t.priority.value,
    )
    if t.id in alarm_by_id:
        elapsed, threshold = alarm_by_id[t.id]
        row += "  [UNDISPATCHED %.0fh > %.0fh threshold]" % (elapsed, threshold)
    if t.id in landed_ids:
        row += "  [ALREADY-LANDED? frob:ticket %s marker found in scope]" % t.id
    # frob:ticket T-1867
    # T-1867: only reachable via `--show-anchors` (doable() excludes
    # anchor=True by default) -- reads as intentionally permanent, not
    # stale/forgotten, when a caller deliberately asks to see anchors.
    if t.anchor:
        row += "  [ANCHOR%s]" % (f": {t.anchor_reason}" if t.anchor_reason else "")
    return row


# frob:ticket T-0976
# frob:ticket T-1822
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping.test_parent_id_not_in_queue_falls_back_to_no_parent_bucket  # noqa: E501
# frob:tests tests/unit/test_app_runners_t0976_mutation_evidence.py::TestRenderDoableDispatchableByParentGrouping.test_parent_id_present_in_queue_uses_its_title  # noqa: E501
def _render_doable_dispatchable(
    ordered: list,
    alarm_by_id: dict,
    queue: "TicketQueue",
    cfg: AppConfig,
    *,
    landed_ids: frozenset[str] = frozenset(),
) -> None:
    """Print the dispatchable section of `frob ticket doable`: a flat
    priority/age/alarm-ordered list, or (`--by-parent`, T-0715) the same
    rows grouped by `parent` so a story's remaining leaves display
    together instead of scattered across one flat list. T-1822: `landed_ids`
    (`_render_already_landed_markers`'s return value) is threaded through
    to `_doable_row` unchanged so a flagged row is marked in EITHER render
    shape, not just the flat one."""
    from frob.app.ticket_runner import _stdout_color

    color = _stdout_color()

    if not cfg.ticket_doable_by_parent:
        for t in ordered:
            _log.info(_doable_row(t, alarm_by_id, color, landed_ids=landed_ids))
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
            _log.info("  %s", _doable_row(t, alarm_by_id, color, landed_ids=landed_ids))


# frob:ticket T-0976
# frob:ticket T-1876
# frob:doc docs/modules/tickets.md#cross-worktree-lease-side-channel-t-0473
# frob:tests tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test_dead_holder_flagged_with_reason  # noqa: E501
# frob:tests tests/unit/test_app_runners_doable_stale_lease.py::TestStaleLeaseReasons.test_live_holder_not_flagged  # noqa: E501
def _stale_lease_reasons(root: Path | None) -> dict[str, str]:
    """`ticket_id -> lease_staleness_reason` for every held lease under
    `root` that `frob.tickets._leases.lease_staleness_reason` judges
    orphaned (T-1876) -- path-gone, ticket-gone, or holder-dead (a lease
    whose `recorded_at` is past `is_lease_ttl_expired`'s horizon AND has
    no live process cwd'd into its worktree, T-1739/T-1806's own
    liveness signals, reused here rather than re-derived). This is the
    read-only surfacing half of T-1876: it FLAGS a dead-looking lease so
    `frob ticket doable`'s in-flight section can say so, and never
    releases or alters anything itself -- reclamation stays an explicit
    `frob worktree release-lease TICKET-ID` call (T-1789/T-1806), the
    conservative posture T-1876 calls for (auto-releasing a merely-slow
    agent's lease would let two worktrees edit the same scope at once,
    the exact T-1868 failure mode). `root=None` (no repo to consult)
    returns an empty map, matching every other lease helper's `root=None`
    convention in this module."""
    if root is None:
        return {}
    from frob.tickets._leases import lease_staleness_reason, orphaned_leases

    reasons: dict[str, str] = {}
    for record in orphaned_leases(root):
        reason = lease_staleness_reason(root, record)
        if reason is not None:
            reasons[record.ticket_id] = reason
    return reasons


# frob:ticket T-1876
def _render_doable_in_flight(
    in_flight: list, stale_reasons: dict[str, str] | None = None
) -> None:
    """Print the "In-flight (leased, already being worked)" section of
    `frob ticket doable`, if any dispatchable-but-leased rows exist.
    T-1876: a row whose lease `stale_reasons` (`_stale_lease_reasons`)
    judges orphaned gets an extra warning line naming the reason and the
    `frob worktree release-lease` recovery command, instead of being
    presented identically to genuinely live work -- the exact gap T-1876
    measured (`doable` listing a dead agent's lease the same as a live
    one, with no signal a coordinator could act on)."""
    if not in_flight:
        return
    from frob.app.ticket_runner import _stdout_color

    color = _stdout_color()
    stale_reasons = stale_reasons if stale_reasons is not None else {}
    _log.info("In-flight (leased, already being worked):")
    for t in in_flight:
        _log.info(
            "  %s  %s  (%s)  priority=%s",
            style_ticket_id(t.id, color),
            t.title,
            t.kind.value,
            t.priority.value,
        )
        reason = stale_reasons.get(t.id)
        if reason is not None:
            _log.warning(
                "    lease looks abandoned (%s) -- if the agent is "
                "genuinely dead, run `frob worktree release-lease %s` "
                "to reclaim it",
                reason,
                t.id,
            )


# frob:ticket T-1738
# frob:ticket T-1825
# frob:tests \
# tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand.test_json_render_shape
# frob:tests tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand.test_plain_render_lists_groups_and_remainder  # noqa: E501
# frob:tests tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand.test_missing_agents_flag_is_a_clean_error  # noqa: E501
def _wave(root: Path, cfg: AppConfig) -> None:
    """Render `frob ticket wave --agents N`: up to N mutually
    scope-disjoint groups from the doable set, plus a remainder section
    naming any doable ticket that could not be placed disjointly and why
    (T-1738). `--json` emits `{"groups": [...], "remainder": [...]}`
    with each group as a plain list of ticket dicts (`model_dump`,
    matching `doable --json`'s per-row shape) and each remainder entry as
    `{"ticket": ..., "colliding_group_index": ..., "colliding_ticket_id":
    ..., "glob": ...}`."""
    from frob.tickets import load_queue
    from frob.tickets._doable import wave

    result = load_queue(root)
    if result.is_err:
        _log.error("ticket wave failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    agents = cfg.ticket_wave_agents
    if agents is None or agents < 1:
        _log.error("ticket wave failed: --agents N is required and must be >= 1")
        sys.exit(1)

    outcome = wave(queue, root, agents=agents, ignore_lease=cfg.ticket_ignore_lease)

    if cfg.ticket_json:
        _render_wave_json(outcome)
        return
    _render_wave_plain(outcome, agents)


# frob:ticket T-1825
def _render_wave_json(outcome) -> None:  # noqa: ANN001 -- WaveResult, deferred-import type
    """`_wave`'s own `--json` render (ARCH001 split): `{"groups": [...],
    "remainder": [...]}`, each group a plain list of ticket dicts
    (`model_dump`, matching `doable --json`'s per-row shape) and each
    remainder entry naming the ticket plus the colliding group/ticket/
    glob that blocked its placement."""
    import json

    payload = {
        "groups": [
            [t.model_dump(mode="json") for t in g.tickets] for g in outcome.groups
        ],
        "remainder": [
            {
                "ticket": r.ticket.model_dump(mode="json"),
                "colliding_group_index": r.colliding_group_index,
                "colliding_ticket_id": r.colliding_ticket_id,
                "glob": r.glob,
            }
            for r in outcome.remainder
        ],
    }
    _log.info(json.dumps(payload, indent=2))


# frob:ticket T-1825
def _render_wave_plain(outcome, agents: int) -> None:  # noqa: ANN001 -- WaveResult, deferred-import type
    """`_wave`'s own human-readable render (ARCH001 split): one line per
    group's tickets, then a "Remainder" section (if any) naming why each
    unplaced ticket could not join an existing group."""
    if not outcome.groups:
        _log.info("zero doable tickets to partition")
        return

    for idx, group in enumerate(outcome.groups):
        _log.info("Group %d (scope: %s):", idx, ", ".join(group.scope) or "(none)")
        for t in group.tickets:
            _log.info(
                "  %s  %s  (%s)  priority=%s",
                t.id,
                t.title,
                t.kind.value,
                t.priority.value,
            )

    if outcome.remainder:
        _log.info(
            "Remainder (could not be placed disjointly, agents=%d requested):",
            agents,
        )
        for r in outcome.remainder:
            _log.info(
                "  %s  %s  collides with group %d via %s (glob %s)",
                r.ticket.id,
                r.ticket.title,
                r.colliding_group_index,
                r.colliding_ticket_id,
                r.glob,
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
    """Large-glob-warning nudges (T-0453) for every ticket PLANNED or
    IN_PROGRESS -- the full per-ticket detail `frob check`'s TICK009
    (T-0714) renders one line per finding for. `frob ticket doable` itself
    only shows a single count line (`_render_scope_breadth_summary`) --
    this function is the shared detail computation both consume. Pass a
    precomputed `breadth` (`scope_breadth_context(root)`) so the breadth
    walk runs once for the whole listing, not once per ticket.

    T-1645: a QUEUED ticket is deliberately excluded, matching TICK009's
    own exemption (`frob.gates._tickets_gate._tick009_scope_breadth_
    nudges`) -- its declared scope is a prediction made before anyone has
    opened the code, not evidence of an over-broad touched set worth
    nudging on yet. This summary's whole point is to describe the same
    outstanding-finding count TICK009 will report on the next `frob
    check`; the two would silently drift apart if only one of them
    dropped the QUEUED case."""
    from frob.tickets import TicketState, large_glob_warnings

    warnings: list[str] = []
    for t in sorted(queue.tickets.values(), key=lambda t: t.id):
        if t.state in (TicketState.IN_PROGRESS, TicketState.PLANNED):
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


# frob:ticket T-1822
# frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers.test_no_markers_prints_nothing_and_returns_empty  # noqa: E501
# frob:tests tests/unit/test_app_runners_t1822_already_landed.py::TestRenderAlreadyLandedMarkers.test_flagged_ticket_prints_one_summary_line_and_is_returned  # noqa: E501
def _render_already_landed_markers(
    root: Path,
    queue: "TicketQueue",
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> frozenset[str]:
    """`frob ticket doable`'s T-1822 wiring of `frob.tickets._doable.
    already_landed_markers` (T-1744 case 1, left deliberately unwired at
    the library level -- that function's own WIRE001 waiver named this
    ticket as the wiring follow-up, now discharged by this call site
    existing): a WARN-severity summary line naming every doable
    candidate whose own `frob:ticket <id>` directive already
    appears in a file its declared scope names, despite the ledger still
    calling it queued/planned. This is the "visible to a coordinator
    BEFORE dispatch" half of this ticket's plan -- the returned id set is
    also threaded into `_render_doable_dispatchable`/`_doable_row` so the
    SAME candidates are individually marked inline in the dispatchable
    listing itself, the "alarm" half.

    Same shape as `_render_scope_breadth_summary` immediately above: a
    single count line rather than one line per finding, so repeated
    `doable` calls do not flood the console -- the per-ticket detail is
    the return value itself (consumed by the caller) plus `frob ticket
    show <id>`'s own scope, which any flagged id's operator would check
    next anyway. Returns the flagged id set (possibly empty) rather than
    `None`, so a caller with no interest in the summary line can still
    get the alarm data without a second `already_landed_markers` call
    (mirrors `breadth` itself: computed once, threaded everywhere)."""
    from frob.tickets._doable import already_landed_markers

    flagged = already_landed_markers(queue, root, breadth=breadth)
    if not flagged:
        return frozenset()
    ids = frozenset(t.id for t in flagged)
    _log.info(
        "%d doable candidate(s) already carry their own landed marker "
        "despite the ledger still calling them queued/planned -- verify "
        "before dispatching: %s",
        len(ids),
        sorted(ids),
    )
    return ids


# frob:ticket T-0453
# frob:ticket T-1743
def _render_doable_show_blocked(
    root: Path,
    queue: "TicketQueue",
    cfg: AppConfig,
    *,
    breadth: tuple[int, tuple[str, ...]] | None = None,
) -> None:
    """Render `frob ticket doable --show-blocked`: every doable-candidate
    currently hidden by an in-progress scope-lease, with the holding
    ticket id, the overlapping glob, and (T-1743) the holder's WORKTREE
    provenance named -- `doable_blocked`'s own `(holder_id, glob)` pairs
    are the exact data `doable` used to decide the block (never
    re-derived here), enriched only with a lookup of WHERE that holder id
    actually comes from.

    T-1743's incident: an id was named as the holder whose OWN declared
    scope (`frob ticket show <id>`) could not have produced the
    collision -- two people spent real time chasing it before finding the
    true holder by hand. `lease_holder_worktree` names the cross-worktree
    lease file's own `worktree` field when one exists for `holder_id`; a
    `None` return means the entry came from the LOCAL ledger's own
    `IN_PROGRESS` row instead (`frob.tickets._doable._in_progress_leases`)
    -- called out explicitly as `(local ledger row, no lease file)` since
    that source can be stale relative to `main` in a way an actively
    written/pruned lease file is not (`frob.tickets._leases`'s own
    module docstring), and is exactly the shape a stale/orphaned
    attribution takes."""
    from frob.tickets import doable_blocked
    from frob.tickets._leases import lease_holder_worktree

    blocked = doable_blocked(queue, root, breadth=breadth)

    if cfg.ticket_json:
        import json

        payload = [
            {
                "ticket": t.model_dump(mode="json"),
                "held_by": [
                    {
                        "ticket_id": holder_id,
                        "glob": glob,
                        "worktree": lease_holder_worktree(root, holder_id)
                        if root is not None
                        else None,
                    }
                    for holder_id, glob in hits
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
        parts = []
        for holder_id, glob in hits:
            worktree = (
                lease_holder_worktree(root, holder_id) if root is not None else None
            )
            provenance = (
                worktree if worktree is not None else "local ledger row, no lease file"
            )
            parts.append(
                f"scope {glob!r} leased by in-progress {holder_id} ({provenance})"
            )
        reasons = "; ".join(parts)
        _log.info("%s  %s  held: %s", style_ticket_id(t.id, color), t.title, reasons)


# frob:ticket T-1492
def _migrate(root: Path, to: str | None = None) -> None:
    """Run `frob ticket migrate`: with `to="v2"`, delegate to
    `migrate_v1_to_v2` (T-1259) to migrate a monofile-mode ledger to
    per-ticket v2 layout; otherwise keep the original collapse-dir-into-
    monofile behavior (T-1492 wires the `--to v2` flag onto this
    dispatch)."""
    if to == "v2":
        from frob.tickets._store import migrate_v1_to_v2

        v2_result = migrate_v1_to_v2(root)
        if v2_result.is_err:
            _log.error("ticket migrate --to v2 failed: %s", v2_result.danger_err)
            sys.exit(1)
        v2_n = v2_result.danger_ok
        if v2_n == 0:
            _log.info("tickets: already v2-mode (or nothing to migrate)")
        else:
            _log.info("migrated %d ticket(s) to v2 layout", v2_n)
        return
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
# frob:ticket T-1882
# frob:tests \
# tests/system/test_cli_ticket.py::TestBulkRenumberCliRemoved.test_no_args_always_refuses  # noqa: E501
# frob:tests \
# tests/system/test_cli_ticket.py::TestBulkRenumberCliRemoved.test_dry_run_still_previews_read_only  # noqa: E501
def _renumber(root: Path, cfg: AppConfig) -> None:
    """`frob ticket renumber <old> <new> [--dry-run]` rewrites one ticket's
    id everywhere (the first-class replacement for the old T-0157-incident
    sed) -- the only way this CLI verb performs a real write.

    T-1882 incident: `frob ticket renumber` with no arguments used to
    perform the legacy whole-ledger contiguous renumber (T-0012) the
    instant it was invoked -- one word shorter than the correct `renumber
    <old> <new>`, with the refusal message for the correct form actively
    advertising it. It renumbered all 273 tickets in one shot.
    Investigated (T-1882 requirement 3) before deciding what to do about
    it: the ONLY thing that ever needed a bulk contiguous renumber --
    fixing a draft id that survived onto the default branch (TICK002) --
    is already served by `frob.gates._fix_engine.fix_tick002_renumber`,
    which calls `finalize_draft` -> the SINGLE-id `renumber_one`, never
    this whole-ledger form. No other production caller of the bulk
    `frob.tickets.renumber` exists (`git grep` confirmed). With no
    legitimate CLI caller, the no-argument dispatch is removed here
    outright rather than guarded -- this repo's standing policy prefers
    deleting a verb with no honest use over adding a mechanism to manage
    it. `frob.tickets.renumber` (the underlying bulk primitive) is left
    in place as a tested library function for a future caller with a
    real need, but the CLI can no longer reach it for real -- only
    `--dry-run` (informational, read-only, harmless) still surfaces it
    here, so an operator retains a way to check contiguity without any
    write path back to it."""
    if cfg.ticket_old_id is not None or cfg.ticket_new_id is not None:
        _renumber_one(root, cfg)
        return

    # frob:ticket T-1882
    if cfg.ticket_dry_run:
        from frob.tickets import renumber

        result = renumber(root, dry_run=True)
        if result.is_err:
            _log.error("ticket renumber --dry-run failed: %s", result.danger_err)
            sys.exit(1)
        n = result.danger_ok
        if n:
            _log.info(
                "DRY RUN: %d ticket(s) are not contiguous (see the preview "
                "above) -- there is no CLI form that applies this whole-"
                "ledger rewrite for real (T-1882); rename one ticket's id "
                "at a time with `frob ticket renumber <old> <new>` instead",
                n,
            )
        else:
            _log.info("ids already contiguous, nothing to renumber")
        return

    _log.error(
        "frob ticket renumber (no arguments) is not supported -- the "
        "whole-ledger bulk rewrite it used to perform (T-0012) renumbered "
        "all 273 tickets in one shot in a real incident and has no known "
        "legitimate caller (T-1882: `fix_tick002_renumber` uses the "
        "single-id `renumber_one` instead). Preview contiguity with "
        "`frob ticket renumber --dry-run`, or rename ONE ticket's id "
        "with `frob ticket renumber <old> <new>`."
    )
    sys.exit(1)


# frob:ticket T-1882
def _renumber_one(root: Path, cfg: AppConfig) -> None:
    """`frob ticket renumber <old> <new>`: rewrite one ticket's id in the
    ledger(s) plus every frob: directive reference across the tracked tree."""
    from frob.tickets import renumber_one

    if cfg.ticket_old_id is None or cfg.ticket_new_id is None:
        # T-1882: this message used to name the no-argument form as the
        # remedy ("...both <old> and <new>, or neither") -- that phrasing
        # is exactly what advertised the destructive bulk form to the
        # agent in the 2026-08-08 incident. Name only the correct,
        # single-id form here.
        _log.error("frob ticket renumber requires both <old> and <new>")
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


# frob:ticket T-1637
# frob:tests tests/system/test_cli_ticket_promote.py::TestPromoteCLI.test_promotes_a_draft_carrying_evidence_and_done_report kind="integration"  # noqa: E501
# frob:tests tests/system/test_cli_ticket_promote.py::TestPromoteCLI.test_promoting_an_already_final_id_is_a_no_op kind="integration"  # noqa: E501
def _promote(root: Path, cfg: AppConfig) -> None:
    """`frob ticket promote <draft-id>`: allocate the next real `T-####`
    id against `root`'s current merged (active+archive) view and rewrite
    the ledger block plus every code reference to it in one atomic
    operation (`finalize_draft`) -- the first-class replacement for the
    lossy hand recipe T-1637 was filed about (read the draft's body out,
    `frob ticket new` a fresh ticket, delete the draft's own block,
    string-swap citations by hand). That recipe drops whatever `frob
    ticket new` cannot recreate -- evidence ids and a Done report, most
    critically (the T-1636 incident: 12 evidence ids and a 12KB Done
    report recoverable only via `git show <sha>~1:tickets.md`
    archaeology). `finalize_draft` is a RENAME, not a copy-then-delete: it
    reuses `renumber_one` to move every field of the SAME `Ticket` object
    (evidence, Done report, scope, state, acceptance -- everything) onto
    the new id, so nothing it already carried can be lost by the
    operation itself.

    A no-op (`Ok(draft_id)` unchanged, logged as a no-op) if `draft_id` is
    already a final id -- callers can call this unconditionally without
    checking `frob.tickets.is_draft_id` themselves first, same contract
    `finalize_draft` itself already promises."""
    from frob.tickets import finalize_draft

    if cfg.ticket_id is None:
        _log.error("frob ticket promote requires a draft id")
        sys.exit(1)

    result = finalize_draft(root, cfg.ticket_id)
    if result.is_err:
        _log.error("ticket promote failed: %s", result.danger_err)
        sys.exit(1)
    final_id = result.danger_ok
    if final_id == cfg.ticket_id:
        _log.info(
            "ticket promote: %s is already a final id, nothing to do", cfg.ticket_id
        )
        return
    _log.info("promoted %s -> %s", cfg.ticket_id, final_id)


# frob:ticket T-0176
