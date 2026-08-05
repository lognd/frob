# frob:waive INV006 reason="T-1270 split of _cli_parsers/_ticket.py's original T-1076 \
# waiver: this module's help/docstring text carries incidental exclusivity-flavored \
# wording (argparse help strings, scope-cut prose) inherited verbatim from the \
# pre-split file, not a new normative contract -- disposed as the same calibration \
# batch, not claim-by-claim"
"""CLI parser builder for the read-only `frob ticket` query subcommands.

Split out of `_cli_parsers/_ticket.py` (T-1270) -- no behavior change, same
argparse tree.
"""

from __future__ import annotations


# frob:ticket T-0030
# frob:ticket T-1100
# frob:waive AFFECT001 reason="T-1100 added a new read-only SUBCOMMAND (flow) to this \
# parser registration function -- the bound agentic-workflow.md #skills/next and \
# #skills/plan doc anchors describe the dispatch-loop/planning skills' USE of frob \
# ticket doable/plan, an orthogonal concern this addition never touches; \
# docs/modules/tickets.md (the doc this change IS actually about) was updated in the \
# same diff"
def _add_ticket_query_parsers(ticket_sub) -> list:
    """Register the read-only `list`/`show`/`doable`/`board`/`epic`/
    `brief`/`flow` ticket subcommands."""
    ticket_list_p = ticket_sub.add_parser("list", help="list tickets")
    # frob:ticket T-0578
    # `--status` is a deprecated back-compat alias for `--state` (the
    # canonical name -- it matches the `ticket_state` field/`state:` ledger
    # key everywhere else): observed misuse (docs/guides/agent-playbook.md)
    # guessed `--status` and got an unrecognized-argument error instead of a
    # result.
    ticket_list_p.add_argument(
        "--state",
        "--status",
        dest="ticket_state",
        help="filter by state (--status accepted as a deprecated alias)",
    )
    ticket_list_p.add_argument("--json", dest="ticket_json", action="store_true")
    # frob:ticket T-1528
    ticket_list_p.add_argument(
        "--stats",
        dest="ticket_stats",
        action="store_true",
        help="append a velocity/ETA line (trailing filed/landed/net rates, "
        "median cycle time, naive burn-down ETA) below the summary footer; "
        "mines the full ledger git history like `frob ticket flow` -- slow "
        "on large histories until T-1330 lands",
    )

    ticket_show_p = ticket_sub.add_parser("show", help="show one ticket")
    ticket_show_p.add_argument("ticket_id", metavar="id")
    ticket_show_p.add_argument("--json", dest="ticket_json", action="store_true")

    ticket_doable_p = ticket_sub.add_parser(
        "doable",
        help="list doable tickets (queued/planned, no open blockers, "
        "scope-lease-safe by default, T-0453)",
    )
    ticket_doable_p.add_argument("--json", dest="ticket_json", action="store_true")
    ticket_doable_p.add_argument(
        "--show-blocked",
        dest="ticket_show_blocked",
        action="store_true",
        help="explain each doable candidate hidden by an in-progress "
        "scope-lease (T-0453), instead of listing the doable set",
    )
    ticket_doable_p.add_argument(
        "--ignore-lease",
        dest="ticket_ignore_lease",
        action="store_true",
        help="skip the T-0453 scope-lease collision filter and return the "
        "raw blocker-only doable list",
    )
    # frob:ticket T-0715
    ticket_doable_p.add_argument(
        "--sprint",
        dest="ticket_doable_sprint",
        metavar="LABEL",
        help="restrict the doable queue to one sprint's commitment (T-0715)",
    )
    # frob:ticket T-0715
    ticket_doable_p.add_argument(
        "--by-parent",
        dest="ticket_doable_by_parent",
        action="store_true",
        help="group the doable list by parent ticket (T-0715) -- a "
        "story's remaining leaves display together instead of one flat "
        "priority/age-ordered list",
    )

    # frob:ticket T-0454
    ticket_board_p = ticket_sub.add_parser(
        "board",
        help="priority-ordered board view, grouped into state columns (T-0454)",
    )
    ticket_board_p.add_argument("--json", dest="ticket_json", action="store_true")
    ticket_board_p.add_argument(
        "--component",
        dest="ticket_board_component",
        help="only show tickets in this component",
    )
    ticket_board_p.add_argument(
        "--label",
        dest="ticket_board_label",
        help="only show tickets carrying this label",
    )

    # frob:ticket T-0454
    ticket_epic_p = ticket_sub.add_parser(
        "epic",
        help="show an epic's full descendant subtree with a done/total rollup (T-0454)",
    )
    ticket_epic_p.add_argument("ticket_id", metavar="id")
    ticket_epic_p.add_argument("--json", dest="ticket_json", action="store_true")

    # frob:ticket T-0568
    ticket_brief_p = ticket_sub.add_parser(
        "brief",
        help="emit the complete agent mission briefing for a ticket (T-0568): "
        "body+acceptance, scope+leases, playbook hard rules, targeted "
        "verify commands, gate baseline, REL/land rules",
    )
    ticket_brief_p.add_argument("ticket_id", metavar="id", nargs="?", default=None)
    # frob:ticket T-1243
    ticket_brief_p.add_argument(
        "--cluster",
        dest="ticket_cluster",
        metavar="EPIC-OR-STORY-ID",
        default=None,
        help="brief every dispatchable descendant of this epic/story as "
        "ONE mission (T-1243): shared playbook rules once, per-ticket "
        "body+acceptance+scope, the union scope lease, and the expected "
        "land cadence -- instead of the single-ticket id positional",
    )

    # frob:ticket T-1100
    ticket_flow_p = ticket_sub.add_parser(
        "flow",
        help="filed/day vs landed/day vs net table + naive burn-down ETA "
        "(T-1100, builds on T-0938's git-history velocity mining)",
    )
    ticket_flow_p.add_argument("--json", dest="ticket_json", action="store_true")

    return [
        ticket_list_p,
        ticket_show_p,
        ticket_doable_p,
        ticket_board_p,
        ticket_epic_p,
        ticket_brief_p,
        ticket_flow_p,
    ]
