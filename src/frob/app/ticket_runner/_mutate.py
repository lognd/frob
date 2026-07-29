# frob:waive REF002 reason="a T-1089 tier-2 split submodule of ticket_runner, \
# imported only by ticket_runner/__init__.py's dispatch table by design -- the \
# same package structure every sibling ticket_runner/_*.py module has, a \
# second consumer would not be genuine"
"""frob.app.ticket_runner._mutate -- the `scope`/`priority`/`kind`/
`component`/`label`/`accept`/`board`/`epic`/`tier`/`sprint`/`brief`/`flow`
mutation command family.

Extracted from `frob.app.ticket_runner` (T-1089, T-0395 tier-2 split
residue). Re-exported from `frob.app.ticket_runner`'s package `__init__`
unchanged so every existing `frob.app.ticket_runner.<name>` call site (CLI
dispatch, tests that monkeypatch these names) keeps working."""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/app/ticket_runner/_mutate.py's \
# exclusivity-vocabulary hits are source-level design-rationale prose \
# (docstrings and comments describing already-implemented internal \
# behavior, verifiable by reading the code they annotate) rather than a \
# separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim -- module prose \
# split verbatim from the pre-T-1089 ticket_runner.py monolith"

from __future__ import annotations

import sys
from pathlib import Path

from frob.app._style import style_state, style_ticket_id
from frob.app.config import AppConfig
from frob.logging import get_logger

from ._new import _scope_closure_warnings

_log = get_logger("frob.app.ticket_runner")


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
    # frob:ticket T-0998
    for warning in _scope_closure_warnings(root, ticket.scope):
        _log.warning("ticket scope %s: scope closure: %s", ticket.id, warning)


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


# frob:ticket T-1029
def _resolve_accept_criteria(cfg: AppConfig) -> list[str]:
    """Resolve `frob ticket accept`'s criteria: `--criterion-file` wins if
    given (parsed via `_new._parse_acceptance_file`, T-0737's blank-line-
    separated-block convention, reused verbatim rather than duplicated),
    else the repeated `--criterion TEXT` flags. Exits 1 if both are given
    (ambiguous which the caller meant) or the file cannot be read -- same
    shape as `_new._resolve_new_acceptance`."""
    from ._new import _parse_acceptance_file

    if cfg.ticket_accept_criterion_file is not None and cfg.ticket_accept_criterion:
        _log.error(
            "frob ticket accept: --criterion and --criterion-file are "
            "mutually exclusive"
        )
        sys.exit(1)
    if cfg.ticket_accept_criterion_file is not None:
        try:
            text = cfg.ticket_accept_criterion_file.read_text(encoding="utf-8")
        except OSError as exc:
            _log.error(
                "ticket accept: could not read --criterion-file %s: %s",
                cfg.ticket_accept_criterion_file,
                exc,
            )
            sys.exit(1)
        return _parse_acceptance_file(text)
    return list(cfg.ticket_accept_criterion)


# frob:ticket T-1029
def _accept(root: Path, cfg: AppConfig) -> None:
    """`frob ticket accept <id> --criterion TEXT... | --criterion-file
    PATH`: the ONLY thing this command does is resolve the criteria
    (`_resolve_accept_criteria`) and forward to `frob.tickets.
    add_acceptance` -- all validation lives there (T-1029, same "this
    command does nothing but forward" pattern as `_scope`/`_label`)."""
    from frob.tickets import add_acceptance

    if cfg.ticket_id is None:
        _log.error("frob ticket accept requires <id>")
        sys.exit(1)

    criteria = _resolve_accept_criteria(cfg)
    if not criteria:
        _log.error(
            "frob ticket accept requires --criterion TEXT or --criterion-file PATH"
        )
        sys.exit(1)

    result = add_acceptance(root, cfg.ticket_id, criteria)
    if result.is_err:
        _log.error("accept failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info(
        "%s: acceptance now %d criterion/criteria (+%d this change)",
        cfg.ticket_id,
        len(ticket.acceptance),
        len(criteria),
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

    from frob.app.ticket_runner import _stdout_color

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

    from frob.app.ticket_runner import _stdout_color

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


# frob:ticket T-1069
def _tier(root: Path, cfg: AppConfig) -> None:
    """`frob ticket tier <id> <epic|story|ticket>`: the ONLY thing this
    command does is forward to `frob.tickets.set_tier` -- no validation is
    re-derived here (T-1069, same pattern as `_priority`/T-0411). `tier` is
    validated strictly against the real `TicketTier` enum inside
    `TicketTier(...)`; an unknown value raises `ValueError`, reported and
    exited the same way an unresolvable ticket id is."""
    from frob.tickets import TicketTier, set_tier

    if cfg.ticket_id is None or cfg.ticket_tier_value is None:
        _log.error("frob ticket tier requires <id> <tier>")
        sys.exit(1)

    try:
        tier = TicketTier(cfg.ticket_tier_value)
    except ValueError:
        _log.error(
            "frob ticket tier: %r is not a valid tier (choose from %s)",
            cfg.ticket_tier_value,
            sorted(t.value for t in TicketTier),
        )
        sys.exit(1)

    result = set_tier(root, cfg.ticket_id, tier)
    if result.is_err:
        _log.error("tier change failed: %s", result.danger_err)
        sys.exit(1)
    ticket = result.danger_ok
    _log.info("%s: tier now %s", cfg.ticket_id, ticket.tier.value)


# frob:ticket T-0715
def _sprint(root: Path, cfg: AppConfig) -> None:
    """Dispatch `frob ticket sprint assign|show` (T-0715) to its handler."""
    if cfg.ticket_sprint_command == "assign":
        _sprint_assign(root, cfg)
    elif cfg.ticket_sprint_command == "show":
        _sprint_show(root, cfg)
    else:
        _log.error("usage: frob ticket sprint <assign|show> ...")
        sys.exit(1)


# frob:ticket T-0715
def _sprint_assign(root: Path, cfg: AppConfig) -> None:
    """`frob ticket sprint assign <id> <label>` (T-0715): set a ticket's
    sprint commitment via `frob.tickets.set_sprint`."""
    from frob.tickets import set_sprint

    if cfg.ticket_id is None or cfg.ticket_sprint is None:
        _log.error("frob ticket sprint assign requires <id> <label>")
        sys.exit(1)
    result = set_sprint(root, cfg.ticket_id, cfg.ticket_sprint)
    if result.is_err:
        _log.error("ticket sprint assign failed: %s", result.danger_err)
        sys.exit(1)
    _log.info("%s sprint set to %s", cfg.ticket_id, cfg.ticket_sprint)


# frob:ticket T-0715
def _sprint_show(root: Path, cfg: AppConfig) -> None:
    """`frob ticket sprint show <label>` (T-0715): render
    `frob.tickets.sprint_view`'s commitment summary -- every ticket
    carrying this sprint label, a state rollup, and closed-count
    velocity."""
    from frob.tickets import load_active, sprint_view

    if cfg.ticket_sprint is None:
        _log.error("frob ticket sprint show requires <label>")
        sys.exit(1)
    result = load_active(root)
    if result.is_err:
        _log.error("ticket sprint show failed: %s", result.danger_err)
        sys.exit(1)
    report = sprint_view(result.danger_ok, cfg.ticket_sprint)

    if cfg.ticket_json:
        import json

        payload = {
            "sprint": report.sprint,
            "tickets": [t.model_dump(mode="json") for t in report.tickets],
            "rollup": {state.value: count for state, count in report.rollup.items()},
            "closed": report.closed,
        }
        _log.info(json.dumps(payload, indent=2))
        return

    from frob.app.ticket_runner import _stdout_color

    color = _stdout_color()
    _log.info(
        "sprint %s -- %d ticket(s), %d closed",
        report.sprint,
        len(report.tickets),
        report.closed,
    )
    for state, count in sorted(report.rollup.items(), key=lambda kv: kv[0].value):
        _log.info("  %s: %d", state.value, count)
    for t in report.tickets:
        _log.info(
            "  %s  [%s]  %s",
            style_ticket_id(t.id, color),
            style_state(t.state.value, color),
            t.title,
        )


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


# frob:ticket T-1100
def _flow(root: Path, cfg: AppConfig) -> None:
    """`frob ticket flow [--json]` (T-1100): render `frob.tickets.
    ticket_flow`'s filed/day vs landed/day vs net table, the current open
    count, and a naive burn-down ETA -- one table, one ETA line, nothing
    re-derived here that `ticket_flow` itself does not already compute."""
    from frob.tickets import load_active, ticket_flow

    result = load_active(root)
    if result.is_err:
        _log.error("ticket flow failed: %s", result.danger_err)
        sys.exit(1)
    queue = result.danger_ok
    report = ticket_flow(root, queue)

    if cfg.ticket_json:
        import json

        payload = {
            "rows": [
                {
                    "day": r.day.isoformat(),
                    "filed": r.filed,
                    "landed": r.landed,
                    "net": r.net,
                }
                for r in report.rows
            ],
            "open_count": report.open_count,
            "trailing_net_rate": report.trailing_net_rate,
            "eta_days": report.eta_days,
        }
        _log.info(json.dumps(payload, indent=2))
        return

    _log.info("%-12s  %6s  %6s  %6s", "day", "filed", "landed", "net")
    for row in report.rows:
        _log.info(
            "%-12s  %6d  %6d  %+6d", row.day.isoformat(), row.filed, row.landed, row.net
        )
    # 3 matches frob.tickets._FLOW_TRAILING_DAYS (T-1100) -- a display-only
    # literal, not re-derived: the actual window width is `ticket_flow`'s
    # own concern, this only labels the number it already returned.
    _log.info(
        "open: %d  trailing-3-day net rate: %+.2f/day",
        report.open_count,
        report.trailing_net_rate,
    )
    if report.eta_days is None:
        _log.info(
            "ETA: cannot estimate (naive extrapolation) -- queue is not "
            "net-shrinking over the trailing window"
        )
    else:
        _log.info(
            "ETA: ~%.1f days to zero-open (naive extrapolation, NOT a forecast)",
            report.eta_days,
        )


# frob:ticket T-0398
