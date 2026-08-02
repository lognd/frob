# frob:waive INV006 reason="T-1270 split of _cli_parsers/_ticket.py's original T-1076 \
# waiver: this module's help/docstring text carries incidental exclusivity-flavored \
# wording (argparse help strings, scope-cut prose) inherited verbatim from the \
# pre-split file, not a new normative contract -- disposed as the same calibration \
# batch, not claim-by-claim"
"""CLI parser builders for the ticket metadata-mutation subcommands:
scope/priority/kind/component/label/accept/tier/sprint.

Split out of `_cli_parsers/_ticket.py` (T-1270) -- no behavior change, same
argparse tree.
"""

from __future__ import annotations


# frob:ticket T-0455
def _add_ticket_scope_parser(ticket_sub):
    """Register `frob ticket scope <id> --add GLOB... --remove GLOB...
    --reason TEXT` -- the formal scope/lease change protocol (T-0455): an
    honest, audited expansion or reduction of a ticket's declared scope
    (and, since the lease is derived live from it, its active tree-lease
    too), replacing the ad-hoc SCOPE001 waive dodge. `--add`/`--remove` may
    each be repeated and may be combined in one call; `--reason` applies to
    every glob the call mutates and is always required."""
    ticket_scope_p = ticket_sub.add_parser(
        "scope",
        help="formally expand/reduce a ticket's declared scope + tree-lease "
        "(T-0455) -- fails loudly on an --add that overlaps another "
        "in-progress ticket's lease",
    )
    ticket_scope_p.add_argument("ticket_id", metavar="id")
    ticket_scope_p.add_argument(
        "--add",
        dest="ticket_scope_add",
        action="append",
        default=[],
        metavar="GLOB",
        help="expand scope + lease to GLOB (repeatable)",
    )
    ticket_scope_p.add_argument(
        "--remove",
        dest="ticket_scope_remove",
        action="append",
        default=[],
        metavar="GLOB",
        help="release GLOB from scope + lease (repeatable)",
    )
    ticket_scope_p.add_argument(
        "--reason",
        dest="ticket_scope_reason",
        metavar="TEXT",
        help="why this scope change (recorded in the ticket's scope_changes "
        "audit trail); required unless --reason-file is given",
    )
    # frob:ticket T-0737
    ticket_scope_p.add_argument(
        "--reason-file",
        dest="ticket_scope_reason_file",
        metavar="PATH",
        help="read the scope-change reason verbatim from PATH instead of "
        "the shell (T-0737); mutually exclusive with --reason",
    )
    return ticket_scope_p


# frob:ticket T-0411
def _add_ticket_priority_parser(ticket_sub):
    """Register `frob ticket priority <id> <level>` -- reprioritize an
    existing ticket (T-0411), the accountable, single-writer alternative to
    hand-editing `tickets.md` frontmatter (same shape as `_add_ticket_scope_
    parser`'s T-0455 precedent)."""
    ticket_priority_p = ticket_sub.add_parser(
        "priority", help="set a ticket's priority (T-0411)"
    )
    ticket_priority_p.add_argument("ticket_id", metavar="id")
    ticket_priority_p.add_argument(
        "ticket_priority_level",
        metavar="level",
        choices=["low", "medium", "high", "critical"],
    )
    return ticket_priority_p


# frob:ticket T-0834
def _add_ticket_kind_parser(ticket_sub):
    """Register `frob ticket kind <id> <kind>` -- correct a mis-filed kind
    (T-0834), same shape as `_add_ticket_priority_parser`'s T-0411
    precedent."""
    ticket_kind_p = ticket_sub.add_parser("kind", help="set a ticket's kind (T-0834)")
    ticket_kind_p.add_argument("ticket_id", metavar="id")
    ticket_kind_p.add_argument(
        "ticket_kind_value",
        metavar="kind",
        choices=["feature", "bug", "security", "ux", "docs", "invariant", "incident"],
    )
    return ticket_kind_p


# frob:ticket T-0454
def _add_ticket_component_parser(ticket_sub):
    """Register `frob ticket component <id> <name>` -- set which module/area
    an existing ticket belongs to (T-0454), same shape as `_add_ticket_
    priority_parser`'s T-0411 precedent. `name` may be the literal string
    "none" to clear it back to uncategorized."""
    ticket_component_p = ticket_sub.add_parser(
        "component", help="set a ticket's component/area (T-0454)"
    )
    ticket_component_p.add_argument("ticket_id", metavar="id")
    ticket_component_p.add_argument("ticket_component", metavar="name")
    return ticket_component_p


# frob:ticket T-0454
def _add_ticket_label_parser(ticket_sub):
    """Register `frob ticket label <id> --add TAG... --remove TAG...` --
    add/remove freeform labels on an existing ticket (T-0454), same shape
    as `_add_ticket_scope_parser`'s T-0455 precedent but with no --reason
    (a label carries no lease-conflict audit trail)."""
    ticket_label_p = ticket_sub.add_parser(
        "label", help="add/remove a ticket's freeform labels (T-0454)"
    )
    ticket_label_p.add_argument("ticket_id", metavar="id")
    ticket_label_p.add_argument(
        "--add",
        dest="ticket_label_add",
        action="append",
        default=[],
        metavar="TAG",
        help="add TAG (repeatable)",
    )
    ticket_label_p.add_argument(
        "--remove",
        dest="ticket_label_remove",
        action="append",
        default=[],
        metavar="TAG",
        help="remove TAG (repeatable)",
    )
    return ticket_label_p


# frob:ticket T-1029
def _add_ticket_accept_parser(ticket_sub):
    """Register `frob ticket accept <id>` -- append (T-1029), amend, or
    remove (T-1422) acceptance criteria on an EXISTING ticket. Exactly one
    mode per invocation:

    - append (default, unchanged since T-1029): `--criterion TEXT... |
      --criterion-file PATH`.
    - `--amend INDEX --text TEXT (--reason TEXT | --reason-file PATH)`:
      replace criterion INDEX's text -- the supported correction for a
      MIS-SPECIFIED criterion (T-1422), instead of hand-editing
      `tickets.md`.
    - `--remove INDEX (--reason TEXT | --reason-file PATH)`: drop
      criterion INDEX outright -- the supported fix for a criterion that
      is UNSATISFIABLE BY CONSTRUCTION (T-1422).

    `--amend`/`--remove` both REQUIRE a reason, recorded in the ticket's
    `acceptance_amendments` audit trail exactly the way `frob ticket
    scope --add/--remove` already records scope changes (T-0455) --
    the reason is the whole point: it is what makes a weakened criterion
    reviewable instead of silently indistinguishable from one that was
    always honest. Both are refused outright on a ticket already in a
    terminal (done/dropped) state."""
    ticket_accept_p = ticket_sub.add_parser(
        "accept",
        help="append (T-1029), amend, or remove (T-1422) acceptance "
        "criteria on an existing ticket",
    )
    ticket_accept_p.add_argument("ticket_id", metavar="id")
    ticket_accept_p.add_argument(
        "--criterion",
        dest="ticket_accept_criterion",
        action="append",
        default=[],
        metavar="TEXT",
        help="acceptance criterion text (repeatable) -- appends",
    )
    ticket_accept_p.add_argument(
        "--criterion-file",
        dest="ticket_accept_criterion_file",
        metavar="PATH",
        help="read criteria verbatim from PATH, one per blank-line-separated "
        "block (T-0737's --acceptance-file convention); mutually exclusive "
        "with --criterion",
    )
    # frob:ticket T-1422
    ticket_accept_p.add_argument(
        "--amend",
        dest="ticket_accept_amend_index",
        type=int,
        metavar="INDEX",
        help="replace acceptance[INDEX]'s text with --text (T-1422); "
        "requires --text and --reason/--reason-file",
    )
    ticket_accept_p.add_argument(
        "--text",
        dest="ticket_accept_amend_text",
        metavar="TEXT",
        help="the replacement criterion text for --amend",
    )
    ticket_accept_p.add_argument(
        "--remove",
        dest="ticket_accept_remove_index",
        type=int,
        metavar="INDEX",
        help="drop acceptance[INDEX] outright (T-1422); requires "
        "--reason/--reason-file",
    )
    ticket_accept_p.add_argument(
        "--reason",
        dest="ticket_accept_amend_reason",
        metavar="TEXT",
        help="why this --amend/--remove happened (recorded in the "
        "ticket's acceptance_amendments audit trail); required for "
        "either, unless --reason-file is given",
    )
    ticket_accept_p.add_argument(
        "--reason-file",
        dest="ticket_accept_amend_reason_file",
        metavar="PATH",
        help="read the --amend/--remove reason verbatim from PATH instead "
        "of the shell (T-1422, T-0737 precedent); mutually exclusive with "
        "--reason",
    )
    return ticket_accept_p


# frob:ticket T-1069
def _add_ticket_tier_parser(ticket_sub):
    """Register `frob ticket tier <id> <epic|story|ticket>` -- reclassify an
    already-created ticket's place in the epic -> story -> ticket hierarchy
    (T-1069), the mutate-in-place counterpart to `frob ticket new --tier`
    (T-0715 created the field but never gave existing tickets a way to
    change it). Same shape as `_add_ticket_priority_parser`'s T-0411
    precedent."""
    ticket_tier_p = ticket_sub.add_parser(
        "tier", help="set an existing ticket's tier (T-1069)"
    )
    ticket_tier_p.add_argument("ticket_id", metavar="id")
    ticket_tier_p.add_argument(
        "ticket_tier_value",
        metavar="tier",
        choices=["epic", "story", "ticket"],
    )
    return ticket_tier_p


# frob:ticket T-0715
def _add_ticket_sprint_parser(ticket_sub):
    """Register `frob ticket sprint assign|show` (T-0715): `assign <id>
    <label>` sets a ticket's sprint commitment, `show <label>` lists every
    ticket committed to it with a state rollup and closed-count velocity
    -- same nested-subcommand shape as `_add_pool_parser`'s `pool
    snapshot|clear` precedent (T-0569)."""
    sprint_p = ticket_sub.add_parser(
        "sprint",
        help="sprint commitment: assign a ticket to a sprint label, or "
        "show a sprint's committed tickets with a state rollup (T-0715)",
    )
    sprint_sub = sprint_p.add_subparsers(dest="ticket_sprint_command")

    assign_p = sprint_sub.add_parser(
        "assign", help="set a ticket's sprint commitment label"
    )
    assign_p.add_argument("ticket_id", metavar="id")
    assign_p.add_argument("ticket_sprint", metavar="label")

    show_p = sprint_sub.add_parser(
        "show",
        help="list every ticket committed to LABEL, with a state rollup "
        "and closed-count velocity",
    )
    show_p.add_argument("ticket_sprint", metavar="label")
    show_p.add_argument("--json", dest="ticket_json", action="store_true")

    return sprint_p
