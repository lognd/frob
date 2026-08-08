"""Register `frob verify status|now|explain|dispose` (T-1697): the CLI
surface over the T-1686 unverified-window package (`frob.verify`)."""

from __future__ import annotations


# frob:ticket T-1697
def _add_verify_parser(sub) -> None:  # noqa: ANN001 -- argparse _SubParsersAction
    """Register the `frob verify` subcommand and its `status`/`now`/
    `explain`/`dispose` actions -- the operable surface over the durable
    verify queue/watermark/quarantine state `frob.verify` already
    maintains (T-1687/T-1692/T-1693)."""
    verify_p = sub.add_parser(
        "verify",
        help="the T-1686 unverified window: depth/age/quarantine status, "
        "force a drain, explain an attribution, dispose a quarantined "
        "finding",
    )
    verify_sub = verify_p.add_subparsers(dest="verify_command")

    status_p = verify_sub.add_parser(
        "status",
        help="watermark age, queue depth/age, quarantine state -- exits "
        "non-zero while quarantine is raised",
    )
    status_p.add_argument("--path", dest="verify_path", metavar="DIR")
    status_p.add_argument("--json", dest="verify_json", action="store_true")

    now_p = verify_sub.add_parser(
        "now", help="drain and verify the queue synchronously, right now"
    )
    now_p.add_argument("--path", dest="verify_path", metavar="DIR")
    now_p.add_argument("--json", dest="verify_json", action="store_true")

    explain_p = verify_sub.add_parser(
        "explain",
        help="print the attribution reachability path for one finding",
    )
    explain_p.add_argument(
        "verify_finding", metavar="RULE:FILE[:LINE]", help="the finding to explain"
    )
    explain_p.add_argument("--path", dest="verify_path", metavar="DIR")
    explain_p.add_argument("--json", dest="verify_json", action="store_true")

    dispose_p = verify_sub.add_parser(
        "dispose",
        help="dispose one or more currently-quarantined findings (file a "
        "ticket or dismiss with a reason) -- clears quarantine only once "
        "every raised finding is disposed",
    )
    dispose_p.add_argument("--path", dest="verify_path", metavar="DIR")
    dispose_p.add_argument("--json", dest="verify_json", action="store_true")
    dispose_p.add_argument(
        "--file-ticket",
        dest="verify_dispose_filed",
        action="append",
        default=[],
        metavar="RULE:FILE:LINE=TICKET",
        help="dispose one finding by naming the real ticket now tracking "
        "it (repeatable; LINE may be empty, e.g. rule:file:=T-0001)",
    )
    dispose_p.add_argument(
        "--dismiss",
        dest="verify_dispose_dismissed",
        action="append",
        default=[],
        metavar="RULE:FILE:LINE=REASON",
        help="dismiss one finding with a human reason (repeatable; LINE "
        "may be empty)",
    )
    dispose_p.add_argument(
        "--reason",
        dest="verify_dispose_reason",
        metavar="TEXT",
        help="the overall clear_quarantine reason (required)",
    )
    dispose_p.add_argument(
        "--actor",
        dest="verify_dispose_actor",
        metavar="NAME",
        help="who/what is clearing this quarantine (default: $USER)",
    )
