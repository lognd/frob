"""CLI wiring for `frob deprecated` (T-0638): list outstanding
`frob:deprecated` entries.

T-0576 landed the `frob:deprecated` directive, the DEPR001-004 gates, and
`frob.gates.list_deprecated`, but left no CLI surface -- this closes that
gap, mirroring `frob debt`'s `frob.app.debt_runner` shape exactly (same
snapshot-load, `--json`/human dual mode, listing-only command). Resolving a
deprecation means removing the symbol and its directive, not running a
command over it -- there is no `--apply` here, matching `frob debt`.
"""

from __future__ import annotations

import contextlib
from datetime import date
from pathlib import Path

from frob.app._snapshot import load_or_build_snapshot
from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)

# Mirrors `frob.gates._OPEN_STATES`'s closed-state set (DONE/DROPPED) for
# a display-side "orphaned" classification -- a ticket in neither state is
# open. Not re-derived from `frob.gates` (private) nor duplicated as a
# second RULE (DEPR002 already owns whether this is a gate violation);
# this is just the human-facing status label T-0638's ticket asked for.
_CLOSED_TICKET_STATES = frozenset({"done", "dropped"})


def _load_ticket_states(root: Path) -> dict[str, str]:
    """Ticket id -> `TicketState.value` for every known ticket (active +
    archive), or `{}` if the queue fails to load -- a missing/unparseable
    ledger degrades to every ticket reading as "orphaned" rather than
    crashing this listing-only command, keeping it useful in a half-broken
    checkout."""
    from frob.tickets import load_queue

    loaded = load_queue(root)
    if loaded.is_err:
        _log.debug("deprecated: ticket queue load failed: %s", loaded.danger_err)
        return {}
    return {tid: t.state.value for tid, t in loaded.danger_ok.tickets.items()}


def _status_of(entry, ticket_states: dict[str, str]) -> str:  # noqa: ANN001
    """One of `orphaned` (ticket missing/closed), `past-sunset`, or
    `in-window` -- the tri-state status T-0638 asked the CLI to surface,
    layered on top of `DeprecatedEntry.expired`, which distinguishes just
    the last two."""
    state = ticket_states.get(entry.ticket)
    if state is None or state in _CLOSED_TICKET_STATES:
        return "orphaned"
    return "past-sunset" if entry.expired else "in-window"


# frob:ticket T-0638
# frob:ticket T-1085
# frob:doc docs/modules/gates.md#deprecated-gate-t-0576
# frob:tests \
# tests/test_deprecated_runner.py::TestDeprecatedRunner.test_json_mode_lists_deprecated\
# _entries  # noqa: E501
# frob:waive AFFECT001 reason="T-1085 (out of this ticket's declared \
# docs/modules/gates.md scope) is a pure internal refactor: this function's \
# snapshot-loading call now goes through the shared \
# frob.app._snapshot.load_or_build_snapshot helper, with the same behavior, \
# output shape, and gate semantics as before; the DEPRECATED-gate doc this \
# anchor covers is unaffected"  # noqa: E501
def run(cfg: AppConfig) -> None:
    """List every outstanding `frob:deprecated` entry under
    `cfg.deprecated_path`, each annotated with its since/sunset/ticket and a
    computed status (`in-window`/`past-sunset`/`orphaned`)."""
    from frob.gates import list_deprecated
    from frob.logging import quiet_stdout_logs

    root = (cfg.deprecated_path or Path(".")).resolve()
    ctx = quiet_stdout_logs() if cfg.deprecated_json else contextlib.nullcontext()
    with ctx:
        snapshot = load_or_build_snapshot(root, log_context="deprecated")
        entries = list_deprecated(snapshot, current_date=date.today().isoformat())
        ticket_states = _load_ticket_states(root)

    statuses = {entry.symref: _status_of(entry, ticket_states) for entry in entries}

    if cfg.deprecated_json:
        import json

        payload = [{**e.model_dump(), "status": statuses[e.symref]} for e in entries]
        _log.info(json.dumps(payload, indent=2, sort_keys=True))
        return

    if not entries:
        _log.info("deprecated: no outstanding frob:deprecated entries")
        return

    _STATUS_ORDER = {"orphaned": 0, "past-sunset": 1, "in-window": 2}
    for entry in sorted(
        entries,
        key=lambda e: (_STATUS_ORDER[statuses[e.symref]], e.symref, e.sunset),
    ):
        _log.info(
            "deprecated: [%s] %s since=%s sunset=%s ticket=%s",
            statuses[entry.symref],
            entry.symref,
            entry.since,
            entry.sunset or "(no sunset)",
            entry.ticket,
        )
