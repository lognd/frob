"""CLI parser builders: the full `frob ticket` subcommand tree.

Split out of `frob.__main__` (T-1076), then split again into per-concern
submodules (T-1270: new/query/progress/closeout/metadata) purely to keep
every file below the large-file gate threshold -- no behavior change, same
argparse tree. This package's public surface (every name importable via
`from frob._cli_parsers._ticket import ...`) is unchanged from the
pre-split single-file module.
"""

from __future__ import annotations

from frob._cli_parsers._reporting import (
    _populate_debt_args,
    _populate_deprecated_args,
)

from ._closeout import (
    _add_ticket_attach_and_lifecycle_end_parsers,
    _add_ticket_close_parser,
    _add_ticket_done_report_parser,
    _add_ticket_fail_evidence_archive_parsers,
    _add_ticket_reverify_parser,
    _add_ticket_review_parser,
    _add_ticket_sweep_async_parser,
)
from ._metadata import (
    _add_ticket_accept_parser,
    _add_ticket_anchor_parser,
    _add_ticket_component_parser,
    _add_ticket_kind_parser,
    _add_ticket_label_parser,
    _add_ticket_priority_parser,
    _add_ticket_runs_last_parser,
    _add_ticket_scope_ack_parser,
    _add_ticket_scope_parser,
    _add_ticket_sprint_parser,
    _add_ticket_tier_parser,
)
from ._new import (
    _add_ticket_new_graph_args,
    _add_ticket_new_identity_args,
    _add_ticket_new_parser,
)
from ._progress import (
    _add_ticket_land_parser,
    _add_ticket_merge_driver_parser,
    _add_ticket_progress_parsers,
    _add_ticket_renumber_parser,
)
from ._query import _add_ticket_query_parsers

__all__ = [
    "_add_ticket_anchor_parser",
    "_add_ticket_attach_and_lifecycle_end_parsers",
    "_add_ticket_close_parser",
    "_add_ticket_closeout_parsers",
    "_add_ticket_component_parser",
    "_add_ticket_done_report_parser",
    "_add_ticket_fail_evidence_archive_parsers",
    "_add_ticket_kind_parser",
    "_add_ticket_label_parser",
    "_add_ticket_land_parser",
    "_add_ticket_lifecycle_parsers",
    "_add_ticket_merge_driver_parser",
    "_add_ticket_new_graph_args",
    "_add_ticket_new_identity_args",
    "_add_ticket_new_parser",
    "_add_ticket_parser",
    "_add_ticket_priority_parser",
    "_add_ticket_progress_parsers",
    "_add_ticket_query_parsers",
    "_add_ticket_renumber_parser",
    "_add_ticket_runs_last_parser",
    "_add_ticket_reverify_parser",
    "_add_ticket_sweep_async_parser",
    "_add_ticket_review_parser",
    "_add_ticket_scope_ack_parser",
    "_add_ticket_scope_parser",
    "_add_ticket_sprint_parser",
    "_add_ticket_tier_parser",
]


# frob:ticket T-0579
def _add_ticket_closeout_parsers(ticket_sub) -> list:
    """Register the ticket closeout subcommands: attach/block/close/
    reverify/fail/evidence/done-report/scope/priority/kind/component/
    label/accept/review/sprint/tier."""
    return (
        _add_ticket_attach_and_lifecycle_end_parsers(ticket_sub)
        + _add_ticket_fail_evidence_archive_parsers(ticket_sub)
        + [
            # frob:ticket T-1005
            _add_ticket_reverify_parser(ticket_sub),
            # frob:ticket T-1684
            _add_ticket_sweep_async_parser(ticket_sub),
            _add_ticket_done_report_parser(ticket_sub),
            _add_ticket_scope_parser(ticket_sub),
            # frob:ticket T-1484
            _add_ticket_scope_ack_parser(ticket_sub),
            # frob:ticket T-1867
            _add_ticket_anchor_parser(ticket_sub),
            _add_ticket_priority_parser(ticket_sub),
            _add_ticket_kind_parser(ticket_sub),
            _add_ticket_component_parser(ticket_sub),
            _add_ticket_label_parser(ticket_sub),
            # frob:ticket T-1029
            _add_ticket_accept_parser(ticket_sub),
            _add_ticket_review_parser(ticket_sub),
            # frob:ticket T-0715
            _add_ticket_sprint_parser(ticket_sub),
            # frob:ticket T-1069
            _add_ticket_tier_parser(ticket_sub),
            # frob:ticket T-1613
            _add_ticket_runs_last_parser(ticket_sub),
        ]
    )


# frob:ticket T-0030
def _add_ticket_lifecycle_parsers(ticket_sub) -> list:
    """Register the state-transition ticket subcommands (plan/start/close/...)."""
    return _add_ticket_progress_parsers(ticket_sub) + _add_ticket_closeout_parsers(
        ticket_sub
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_ticket_parser(sub) -> None:
    """Register the `frob ticket` subcommand and its arguments."""
    ticket_p = sub.add_parser("ticket", help="the statically-checkable ticket queue")
    ticket_p.add_argument(
        "-v",
        "--verbose",
        dest="ticket_verbose",
        action="count",
        default=0,
        help=(
            "restore diagnostic INFO/DEBUG log lines (gitio/tickets loader "
            "chatter); default shows ticket output and WARNING+ only (T-0768)"
        ),
    )
    ticket_sub = ticket_p.add_subparsers(dest="ticket_command")
    _add_ticket_new_parser(ticket_sub)
    path_parsers = _add_ticket_query_parsers(ticket_sub)
    path_parsers += _add_ticket_lifecycle_parsers(ticket_sub)
    for _tp in path_parsers:
        _tp.add_argument("--path", dest="ticket_path", metavar="DIR", default=".")

    # T-1570: `debt`/`deprecated` are ticket-adjacent (disclosed-and-
    # tracked deferred work, same shape as the ticket queue without the
    # lifecycle) -- resolved as `frob ticket debt`/`frob ticket
    # deprecated` siblings of every other subcommand here, NOT a new
    # top-level `frob tickets` (plural) parent that would just contain
    # this existing singular verb group. Standalone `frob debt`/`frob
    # deprecated` stay permanent aliases (docs/design/cli-regrouping.md).
    ticket_debt_p = ticket_sub.add_parser(
        "debt", help="list outstanding frob:debt entries (rule, site, ticket, until)"
    )
    _populate_debt_args(ticket_debt_p)
    ticket_deprecated_p = ticket_sub.add_parser(
        "deprecated",
        help="list outstanding frob:deprecated entries (symref, since, "
        "sunset, ticket, status)",
    )
    _populate_deprecated_args(ticket_deprecated_p)
