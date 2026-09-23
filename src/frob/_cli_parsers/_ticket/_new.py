"""CLI parser builder for `frob ticket new`: identity/graph/body creation flags.

Split out of `_cli_parsers/_ticket.py` (T-1270), itself split out of
`frob.__main__` (T-1076), purely to keep files below the large-file gate
threshold -- no behavior change, same argparse tree.
"""

# frob:ticket T-5134
from __future__ import annotations

# frob:ticket T-3614
# T-3614: `--wait`'s sensible default budget when passed bare (no
# SECONDS given) -- distinct from `frob.tickets._leases._LAND_WAIT_
# TIMEOUT_S` (330.0, that module's own internal default when NO wait
# was requested at all): a caller that explicitly asked to wait wants a
# shorter, CLI-scale budget by default, not this repo's full land-
# duration ceiling.
_TICKET_WAIT_DEFAULT_S = 60.0


# frob:ticket T-3614
def _add_ticket_wait_arg(parser) -> None:  # noqa: ANN001
    """Register `--wait [SECONDS]` on `parser` (T-3614): a write verb that
    hits a held `LandInProgress`/`tickets.lock` window used to fail
    instantly, forcing every caller to hand-roll a sleep loop around the
    retry. `--wait` (bare) blocks up to `_TICKET_WAIT_DEFAULT_S`; `--wait
    N` blocks up to `N` seconds; omitted entirely (`ticket_wait_s` stays
    `None`) is today's unchanged instant-refusal behavior. Threaded by
    `frob.app.ticket_runner._refuse_if_land_in_progress_for_dispatch` to
    `frob.tickets._leases.refuse_if_land_in_progress`'s existing `wait_
    timeout_s` parameter, which already implements the poll-with-backoff
    wait loop (T-1961/T-2023) -- this flag is the only piece that was
    missing to reach it from the CLI. Shared by every one of the six
    ticket-write verbs this ticket names (`new`, `drop`, `body`, `scope`,
    `fail`, `reconcile`) rather than each re-declaring an identical
    flag."""
    parser.add_argument(
        "--wait",
        dest="ticket_wait_s",
        nargs="?",
        const=_TICKET_WAIT_DEFAULT_S,
        type=float,
        default=None,
        metavar="SECONDS",
        help="block on a held LandInProgress/tickets.lock window instead "
        "of refusing instantly; bare --wait uses a "
        f"{_TICKET_WAIT_DEFAULT_S:.0f}s default budget, --wait N uses N "
        "seconds, omitted is today's unchanged instant-refusal behavior",
    )


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
        "medium) -- `frob ticket doable` orders highest priority "
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
        "hierarchy (default: ticket, a plain leaf)",
    )
    # frob:ticket T-0715
    ticket_new_p.add_argument(
        "--sprint",
        dest="ticket_sprint",
        metavar="LABEL",
        help="free-form sprint commitment label (e.g. 2026-W30, "
        "sprint-14); omit for uncommitted/backlog",
    )
    # frob:ticket T-2574
    ticket_new_p.add_argument(
        "--milestone",
        dest="ticket_milestone",
        metavar="VALUE",
        help="which shippable milestone this ticket belongs to, a real "
        "semver string (e.g. 1.10.0); omit for unmilestoned",
    )
    # frob:ticket T-5132
    ticket_new_p.add_argument(
        "--points",
        dest="ticket_points",
        type=int,
        metavar="N",
        help="story-point size, one of the Fibonacci sizes 1 2 3 5 8 13"
        "; WARNs if omitted -- required before `frob ticket "
        "start` unless --unsized-ack is used there",
    )
    # frob:ticket T-0454
    ticket_new_p.add_argument(
        "--component",
        dest="ticket_component",
        help="which module/area this ticket belongs to (freeform)",
    )
    ticket_new_p.add_argument(
        "--label",
        dest="ticket_labels",
        action="append",
        default=[],
        metavar="TAG",
        help="freeform organizational tag, orthogonal to --component (repeatable)",
    )
    # frob:ticket T-2760
    ticket_new_p.add_argument(
        "--finding",
        dest="ticket_findings",
        action="append",
        default=[],
        metavar="RULE:FILE",
        help="a 'RULE:FILE' gate-finding identity this ticket exists to "
        "resolve (repeatable); a second open ticket declaring the "
        "SAME (rule, file) pair is refused at filing time and warned "
        "about at start time, naming this one",
    )


# frob:ticket T-0030
# frob:waive AFFECT001 reason="T-2302 added \
# --scope-breadth-ack/--scope-breadth-ack-reason flags to this same \
# parser-registration function; the two affects()-closure docs \
# (docs/guides/agentic-workflow.md#implement-strictly-within-scope-add-frobticket--frobtests-directives, #the-humanai-split) describe general scope/frob:ticket discipline and the human/AI split, unaffected by adding two more argparse flags here -- content stays true, already re-acked via frob ack (T-2302)"  # noqa: E501
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
        help="read the ticket body verbatim from PATH instead of the shell"
        "; mutually exclusive with --body",
    )
    # frob:ticket T-0737
    ticket_new_p.add_argument(
        "--acceptance-file",
        dest="ticket_acceptance_file",
        metavar="PATH",
        help="read acceptance criteria from PATH, blank-line-separated "
        "blocks; mutually exclusive with --acceptance",
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
        help="skip auto-commit of the new ticket's ledger block "
        "(parity with `start`'s auto-commit) -- for a caller that "
        "wants to batch several ledger writes into one commit of its own",
    )
    # frob:ticket T-1995
    ticket_new_p.add_argument(
        "--ack-related",
        dest="ticket_ack_related",
        action="store_true",
        help="acknowledge the related-ticket surfacing check ("
        "checks open/done/archived tickets by title similarity) and "
        "proceed even though a close match was found -- required only "
        "when the check actually surfaces a candidate; a genuinely novel "
        "title needs no flag",
    )
    _add_ticket_wait_arg(ticket_new_p)
    # frob:ticket T-2302
    ticket_new_p.add_argument(
        "--scope-breadth-ack",
        dest="ticket_scope_breadth_ack",
        action="store_true",
        help="acknowledge a deliberately broad --scope at FILING time "
        "(the filing-time twin of `frob ticket scope-ack`): sets "
        "scope_breadth_ack=True on the new ticket immediately, the same "
        "field `frob ticket scope-ack <id>` sets after the fact, so the "
        "filing-time breadth WARN never fires for a ticket that "
        "already declared its broad scope intentional -- requires "
        "--scope-breadth-ack-reason",
    )
    # frob:ticket T-2302
    ticket_new_p.add_argument(
        "--scope-breadth-ack-reason",
        dest="ticket_scope_breadth_ack_reason",
        metavar="TEXT",
        help="required justification for --scope-breadth-ack, "
        "same non-blank requirement `frob ticket scope-ack --reason` "
        "already enforces",
    )
    # frob:ticket T-2624
    ticket_new_p.add_argument(
        "--runs-last-parallel-safe",
        dest="ticket_runs_last_parallel_safe",
        action="store_true",
        help="declare this ticket safe to run in parallel with another "
        "runs_last ticket in the same milestone at FILING time ("
        "the filing-time twin of `frob ticket runs-last-parallel-safe`): "
        "sets runs_last_parallel_safe=True immediately, so MILE004 never "
        "fires for an unordered pair that already declared itself "
        "parallel-safe -- requires --runs-last-parallel-safe-reason",
    )
    # frob:ticket T-2624
    ticket_new_p.add_argument(
        "--runs-last-parallel-safe-reason",
        dest="ticket_runs_last_parallel_safe_reason",
        metavar="TEXT",
        help="required justification for --runs-last-parallel-safe"
        ", same non-blank requirement "
        "`frob ticket runs-last-parallel-safe --reason` already enforces",
    )
