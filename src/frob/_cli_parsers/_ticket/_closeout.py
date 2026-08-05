# frob:waive INV006 reason="T-1270 split of _cli_parsers/_ticket.py's original T-1076 \
# waiver: this module's help/docstring text carries incidental exclusivity-flavored \
# wording (argparse help strings, scope-cut prose) inherited verbatim from the \
# pre-split file, not a new normative contract -- disposed as the same calibration \
# batch, not claim-by-claim"
"""CLI parser builders for the ticket closeout subcommands: attach/block/
close/reverify/review/fail/evidence/drop/archive/done-report.

Split out of `_cli_parsers/_ticket.py` (T-1270) -- no behavior change, same
argparse tree.
"""

from __future__ import annotations


def _add_ticket_attach_and_lifecycle_end_parsers(ticket_sub) -> list:
    """Register `attach`/`block`/`close`: the non-evidence closeout subcommands."""
    ticket_attach_p = ticket_sub.add_parser(
        "attach", help="attach a file or clipboard image to a ticket"
    )
    ticket_attach_p.add_argument("ticket_id", metavar="id")
    ticket_attach_p.add_argument(
        "ticket_attach_path", metavar="path", nargs="?", default=None
    )
    ticket_attach_p.add_argument("--caption", dest="ticket_caption", default="")

    ticket_block_p = ticket_sub.add_parser("block", help="record a blocker")
    ticket_block_p.add_argument("ticket_id", metavar="id")
    ticket_block_p.add_argument("--by", dest="ticket_by", required=True)

    ticket_close_p = _add_ticket_close_parser(ticket_sub)
    return [ticket_attach_p, ticket_block_p, ticket_close_p]


def _add_ticket_close_parser(ticket_sub):
    """Register `frob ticket close` and return its subparser."""
    ticket_close_p = ticket_sub.add_parser("close", help="transition to done")
    ticket_close_p.add_argument("ticket_id", metavar="id")
    ticket_close_p.add_argument(
        "--evidence",
        dest="ticket_evidence_ids",
        action="append",
        default=[],
        metavar="NODE-ID",
        help="pytest node id to record as evidence before closing (repeatable)",
    )
    ticket_close_p.add_argument(
        "--evidence-cmd",
        dest="ticket_evidence_cmd",
        metavar="COMMAND",
        help="non-pytest evidence channel (T-0215): run COMMAND, record its "
        "exit status and an output digest as evidence before closing -- "
        "docs-kind tickets only, code kinds still require --evidence node ids",
    )
    ticket_close_p.add_argument(
        "--accepts",
        dest="ticket_accepts",
        action="append",
        type=int,
        default=[],
        metavar="INDEX",
        help="T-0572: 0-based ticket.acceptance index that --evidence/"
        "--evidence-cmd's id(s) also bind to (repeatable); an unbound "
        "acceptance criterion refuses the close",
    )
    # frob:ticket T-0571
    ticket_close_p.add_argument(
        "--strict",
        dest="ticket_close_strict",
        action="store_true",
        help="require an approve-verdict `frob ticket review` record "
        "naming the current commit before closing (T-0571); combined with "
        "`[tickets] require_review_for_close` in frob.toml, which must "
        "also be true for this to actually gate -- off by default",
    )
    # frob:ticket T-0844
    ticket_close_p.add_argument(
        "--skip-mutation-evidence",
        dest="ticket_close_skip_mutation_evidence",
        action="store_true",
        help=(
            "T-0844 escape hatch (the close-path twin of `frob ticket land "
            "--skip-mutation-evidence`): do not let a TEST016 confirmatory-"
            "only-evidence finding refuse the close (the check still runs "
            "and logs its findings at WARNING; this only stops it from "
            "blocking). Use for a genuine false positive, not to wave "
            "through real confirmatory evidence."
        ),
    )
    # frob:ticket T-1178
    ticket_close_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1178's auto-commit of the close ledger change "
        "(parity with `new`/`drop`/`fail`'s T-1130 auto-commit)",
    )
    return ticket_close_p


# frob:ticket T-1005
def _add_ticket_reverify_parser(ticket_sub):
    """Register `frob ticket reverify <id>` -- re-run the full close-time
    verification suite (evidence re-run, mutation evidence, covers-scope,
    acceptance binding, live-tracker citation) against an already-DONE
    ticket and refresh its recap, with NO state transition (T-1005, the
    post-close send-back verb `close`/`start`/`sweep` all refuse to be).
    Shares `close`'s own `--evidence`/`--evidence-cmd`/`--accepts`/
    `--strict`/`--skip-mutation-evidence` flags verbatim (same dest names,
    so `frob.app.ticket_runner._close_guards_for_ticket` works unmodified
    for either command) plus `done-report`'s `--base-ref` (the recap
    refresh re-derives the Changed section against it)."""
    ticket_reverify_p = ticket_sub.add_parser(
        "reverify",
        help="re-run close verification on a done ticket, refresh its "
        "recap, no state transition",
    )
    ticket_reverify_p.add_argument("ticket_id", metavar="id")
    ticket_reverify_p.add_argument(
        "--evidence",
        dest="ticket_evidence_ids",
        action="append",
        default=[],
        metavar="NODE-ID",
        help="pytest node id to record as evidence before reverifying (repeatable)",
    )
    ticket_reverify_p.add_argument(
        "--evidence-cmd",
        dest="ticket_evidence_cmd",
        metavar="COMMAND",
        help="non-pytest evidence channel (T-0215), same semantics as "
        "`close --evidence-cmd`",
    )
    ticket_reverify_p.add_argument(
        "--accepts",
        dest="ticket_accepts",
        action="append",
        type=int,
        default=[],
        metavar="INDEX",
        help="T-0572: 0-based ticket.acceptance index --evidence/"
        "--evidence-cmd's id(s) also bind to (repeatable)",
    )
    ticket_reverify_p.add_argument(
        "--strict",
        dest="ticket_close_strict",
        action="store_true",
        help="require an approve-verdict `frob ticket review` record "
        "naming the current commit (T-0571), same semantics as "
        "`close --strict`",
    )
    ticket_reverify_p.add_argument(
        "--skip-mutation-evidence",
        dest="ticket_close_skip_mutation_evidence",
        action="store_true",
        help="T-0844 escape hatch, same semantics as `close --skip-mutation-evidence`",
    )
    ticket_reverify_p.add_argument(
        "--base-ref",
        dest="ticket_base_ref",
        default="main",
        metavar="REF",
        help="base ref the refreshed recap's Changed section diffs "
        "against (default: main)",
    )
    return ticket_reverify_p


# frob:ticket T-0571
def _add_ticket_review_parser(ticket_sub):
    """Register `frob ticket review <id> --verdict approve|reject
    --reviewer NAME --findings-file PATH [--commit SHA]` (T-0571): writes a
    structured review record (verdict, reviewer, findings summary,
    timestamp, commit reviewed) into the ticket's ledger entry as
    first-class evidence -- the fix for adversarial review's verdict living
    only in dispatch-chat prose."""
    ticket_review_p = ticket_sub.add_parser(
        "review",
        help="record a structured adversarial-review verdict (T-0571)",
    )
    ticket_review_p.add_argument("ticket_id", metavar="id")
    ticket_review_p.add_argument(
        "--verdict",
        dest="ticket_review_verdict",
        required=True,
        choices=["approve", "reject"],
        help="the reviewer's verdict",
    )
    ticket_review_p.add_argument(
        "--reviewer",
        dest="ticket_reviewer",
        required=True,
        metavar="NAME",
        help="who performed the review",
    )
    ticket_review_p.add_argument(
        "--findings-file",
        dest="ticket_findings_file",
        required=True,
        metavar="PATH",
        help="file containing the findings summary",
    )
    ticket_review_p.add_argument(
        "--commit",
        dest="ticket_review_commit",
        metavar="SHA",
        help="the commit reviewed (default: current HEAD)",
    )
    return ticket_review_p


# frob:ticket T-0579
def _add_ticket_fail_evidence_archive_parsers(ticket_sub) -> list:
    """Register `fail`/`drop`/`evidence`/`archive`: the remaining closeout
    subcommands."""
    ticket_fail_p = ticket_sub.add_parser(
        "fail", help="record a failed attempt in the failure log"
    )
    ticket_fail_p.add_argument("ticket_id", metavar="id")
    ticket_fail_p.add_argument("--summary", dest="ticket_summary", required=True)
    # frob:ticket T-1130
    ticket_fail_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1130's auto-commit of the fail-log/requeue ledger "
        "change (parity with `start`'s T-1054 auto-commit)",
    )

    ticket_evidence_p = ticket_sub.add_parser(
        "evidence",
        help="append pytest node ids to a ticket's structured evidence list",
    )
    ticket_evidence_p.add_argument("ticket_id", metavar="id")
    ticket_evidence_p.add_argument(
        "ticket_evidence_ids", metavar="node-id", nargs="*", default=[]
    )
    ticket_evidence_p.add_argument(
        "--evidence-cmd",
        dest="ticket_evidence_cmd",
        metavar="COMMAND",
        help="non-pytest evidence channel (T-0215): run COMMAND, record its "
        "exit status and an output digest as evidence -- docs-kind tickets "
        "only, code kinds still require pytest node ids",
    )
    # frob:ticket T-1537
    ticket_evidence_p.add_argument(
        "--replace",
        dest="ticket_evidence_replace",
        nargs=2,
        metavar=("OLD-NODE-ID", "NEW-NODE-ID"),
        default=[],
        help="rebind one evidence id everywhere it appears (the flat "
        "evidence list AND every acceptance criterion's own binding) in "
        "one atomic write -- for a renamed/parametrized test whose old "
        "node id no longer resolves; mutually usable alongside positional "
        "node-id ids/--evidence-cmd in the same invocation",
    )
    # frob:ticket T-1561
    ticket_evidence_p.add_argument(
        "--archived",
        dest="ticket_evidence_archived",
        action="store_true",
        help="with --replace, target an ARCHIVED ticket instead of an "
        "active one -- COV003 scans tickets-archive.md/tickets/archive/** "
        "too, so a stale evidence binding on an already-archived ticket "
        "needs this to be reachable at all (T-1561)",
    )
    ticket_evidence_p.add_argument(
        "--accepts",
        dest="ticket_accepts",
        action="append",
        type=int,
        default=[],
        metavar="INDEX",
        help="T-0572: 0-based ticket.acceptance index the node id(s) above "
        "also bind to (repeatable) -- binds evidence to a specific "
        "acceptance criterion instead of only the ticket's flat evidence "
        "list",
    )
    # frob:ticket T-1178
    ticket_evidence_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1178's auto-commit of the evidence ledger change "
        "(parity with `new`/`drop`/`fail`'s T-1130 auto-commit)",
    )

    ticket_drop_p = ticket_sub.add_parser(
        "drop",
        help="transition to dropped with a dated --reason (T-0579): "
        "absorbed elsewhere, obsolete, or subsumed work",
    )
    ticket_drop_p.add_argument("ticket_id", metavar="id")
    ticket_drop_p.add_argument(
        "--reason", dest="ticket_reason", required=True, metavar="TEXT"
    )
    ticket_drop_p.add_argument(
        "--absorbed-by",
        dest="ticket_absorbed_by",
        default=None,
        metavar="T-####",
        help="cross-reference the ticket this work was folded into",
    )
    # frob:ticket T-1130
    ticket_drop_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1130's auto-commit of the drop ledger change (parity "
        "with `start`'s T-1054 auto-commit)",
    )

    ticket_archive_p = ticket_sub.add_parser(
        "archive", help="move done/dropped tickets into tickets-archive.md"
    )
    ticket_archive_p.add_argument(
        "--force",
        dest="ticket_force",
        action="store_true",
        help="T-0810: override the T-0764 refusal when a live cross-"
        "worktree lease exists anywhere in the repo -- archive anyway",
    )
    return [ticket_fail_p, ticket_evidence_p, ticket_drop_p, ticket_archive_p]


# frob:ticket T-0458
def _add_ticket_done_report_parser(ticket_sub):
    """Register `frob ticket done-report <id> (--why TEXT | --why-file PATH)`
    -- the atomic, auto-composing Done-report writer (T-0458): the caller
    supplies ONLY the narrative why; Changed and Evidence are auto-filled
    from git and the ticket's recorded evidence. `--why -` (or neither flag
    given) reads the narrative from stdin."""
    ticket_done_report_p = ticket_sub.add_parser(
        "done-report",
        help="atomically write/update a ticket's Done report (Changed + "
        "Evidence auto-composed -- never hand-edit tickets.md)",
    )
    ticket_done_report_p.add_argument("ticket_id", metavar="id")
    # frob:ticket T-0578
    # `--body` is a deprecated back-compat alias for `--why` (the canonical
    # name here -- `new`'s own `--body` means something different, the
    # ticket's initial description, which is exactly the cross-subcommand
    # naming drift T-0578 exists to close): observed misuse guessed
    # `--body` for the Done-report narrative and got an unrecognized-
    # argument error instead of a result.
    ticket_done_report_p.add_argument(
        "--why",
        "--body",
        dest="ticket_why",
        metavar="TEXT",
        help="the narrative why (pass '-' or omit both --why/--why-file to "
        "read from stdin; --body accepted as a deprecated alias)",
    )
    ticket_done_report_p.add_argument(
        "--why-file",
        dest="ticket_why_file",
        metavar="PATH",
        help="read the narrative why from PATH",
    )
    ticket_done_report_p.add_argument(
        "--base-ref",
        dest="ticket_base_ref",
        default="main",
        metavar="REF",
        help="base ref the auto-filled Changed section diffs against (default: main)",
    )
    # frob:ticket T-1178
    ticket_done_report_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1178's auto-commit of the done-report ledger change "
        "(parity with `new`/`drop`/`fail`'s T-1130 auto-commit)",
    )
    return ticket_done_report_p
