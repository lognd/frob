"""CLI parser builder for `frob ticket new`: identity/graph/body creation flags.

Split out of `_cli_parsers/_ticket.py` (T-1270), itself split out of
`frob.__main__` (T-1076), purely to keep files below the large-file gate
threshold -- no behavior change, same argparse tree.
"""

from __future__ import annotations


def _add_ticket_new_identity_args(ticket_new_p) -> None:
    """Register `frob ticket new`'s title/kind/acceptance/threat classification args."""
    ticket_new_p.add_argument("--title", dest="ticket_title", required=True)
    ticket_new_p.add_argument(
        "--kind",
        dest="ticket_kind",
        required=True,
        choices=["feature", "bug", "security", "ux", "docs", "invariant", "incident"],
    )
    ticket_new_p.add_argument(
        "--acceptance",
        dest="ticket_acceptance",
        action="append",
        default=[],
        metavar="CRITERION",
        help="given/when/then acceptance criterion (repeatable)",
    )
    ticket_new_p.add_argument(
        "--threat",
        dest="ticket_threat",
        choices=[
            "spoofing",
            "tampering",
            "repudiation",
            "info-disclosure",
            "denial-of-service",
            "elevation-of-privilege",
        ],
        help="STRIDE category for a kind=security ticket",
    )
    # frob:ticket T-0411
    ticket_new_p.add_argument(
        "--priority",
        dest="ticket_priority",
        choices=["low", "medium", "high", "critical"],
        help="how important this ticket is, independent of age (default: "
        "medium, T-0411) -- `frob ticket doable` orders highest priority "
        "first",
    )


def _add_ticket_new_graph_args(ticket_new_p) -> None:
    """Register `frob ticket new`'s origin/scope/blocked-by/parent graph-edge args."""
    ticket_new_p.add_argument(
        "--origin",
        dest="ticket_origin",
        choices=["human", "agent", "auditor"],
        help="who filed this ticket (default: human)",
    )
    ticket_new_p.add_argument(
        "--scope", dest="ticket_scope", action="append", default=[]
    )
    ticket_new_p.add_argument(
        "--blocked-by", dest="ticket_blocked_by", action="append", default=[]
    )
    ticket_new_p.add_argument("--parent", dest="ticket_parent")
    # frob:ticket T-0715
    ticket_new_p.add_argument(
        "--tier",
        dest="ticket_tier",
        choices=["epic", "story", "ticket"],
        help="where this ticket sits in the epic -> story -> ticket "
        "hierarchy (default: ticket, a plain leaf, T-0715)",
    )
    # frob:ticket T-0715
    ticket_new_p.add_argument(
        "--sprint",
        dest="ticket_sprint",
        metavar="LABEL",
        help="free-form sprint commitment label (e.g. 2026-W30, "
        "sprint-14, T-0715); omit for uncommitted/backlog",
    )
    # frob:ticket T-0454
    ticket_new_p.add_argument(
        "--component",
        dest="ticket_component",
        help="which module/area this ticket belongs to (freeform, T-0454)",
    )
    ticket_new_p.add_argument(
        "--label",
        dest="ticket_labels",
        action="append",
        default=[],
        metavar="TAG",
        help="freeform organizational tag, orthogonal to --component "
        "(repeatable, T-0454)",
    )


# frob:ticket T-0030
def _add_ticket_new_parser(ticket_sub) -> None:
    """Register `frob ticket new` and its (many) creation flags."""
    ticket_new_p = ticket_sub.add_parser("new", help="create a new ticket")
    _add_ticket_new_identity_args(ticket_new_p)
    _add_ticket_new_graph_args(ticket_new_p)
    ticket_new_p.add_argument("--body", dest="ticket_body", default="")
    # frob:ticket T-0737
    ticket_new_p.add_argument(
        "--body-file",
        dest="ticket_body_file",
        metavar="PATH",
        help="read the ticket body verbatim from PATH instead of the shell "
        "(T-0737); mutually exclusive with --body",
    )
    # frob:ticket T-0737
    ticket_new_p.add_argument(
        "--acceptance-file",
        dest="ticket_acceptance_file",
        metavar="PATH",
        help="read acceptance criteria from PATH, blank-line-separated "
        "blocks (T-0737); mutually exclusive with --acceptance",
    )
    ticket_new_p.add_argument("--json", dest="ticket_json", action="store_true")
    ticket_new_p.add_argument("--path", dest="ticket_path", metavar="DIR", default=".")
    ticket_new_p.add_argument(
        "--evidence",
        dest="ticket_evidence_ids",
        action="append",
        default=[],
        metavar="NODE-ID",
        help="pytest node id to record as evidence on the new ticket (repeatable)",
    )
    # frob:ticket T-1130
    ticket_new_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1130's auto-commit of the new ticket's ledger block "
        "(parity with `start`'s T-1054 auto-commit) -- for a caller that "
        "wants to batch several ledger writes into one commit of its own",
    )
