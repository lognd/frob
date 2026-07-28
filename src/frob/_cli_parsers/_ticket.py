# frob:waive INV006 reason="T-1076 split of __main__.py's original T-0585 waiver: \
# this module's help/docstring text carries incidental exclusivity-flavored wording \
# (argparse help strings, scope-cut prose) inherited verbatim from __main__.py, not a \
# new normative contract -- disposed as the same calibration batch, not claim-by-claim"
"""CLI parser builders: the full `frob ticket` subcommand tree.

Split out of `frob.__main__` (T-1076) purely to keep that module below the
large-file gate threshold -- no behavior change, same argparse tree.
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


# frob:ticket T-0030
def _add_ticket_query_parsers(ticket_sub) -> list:
    """Register the read-only `list`/`show`/`doable` ticket subcommands."""
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
    ticket_brief_p.add_argument("ticket_id", metavar="id")

    return [
        ticket_list_p,
        ticket_show_p,
        ticket_doable_p,
        ticket_board_p,
        ticket_epic_p,
        ticket_brief_p,
    ]


def _add_ticket_progress_parsers(ticket_sub) -> list:
    """Register the state-only ticket transitions: plan/requeue/start/sweep/
    migrate/renumber."""
    ticket_plan_p = ticket_sub.add_parser("plan", help="transition queued -> planned")
    ticket_plan_p.add_argument("ticket_id", metavar="id")

    ticket_requeue_p = ticket_sub.add_parser(
        "requeue",
        help="transition in-progress -> queued (releases the T-0453 lease) "
        "for a parked or mis-started ticket",
    )
    ticket_requeue_p.add_argument("ticket_id", metavar="id")
    ticket_requeue_p.add_argument("--reason", dest="ticket_reason", default=None)

    ticket_start_p = ticket_sub.add_parser(
        "start",
        help="transition to in-progress (auto-plans a queued ticket) and "
        "BACKGROUND the pre-work sweep (T-0474; --foreground blocks instead)",
    )
    ticket_start_p.add_argument("ticket_id", metavar="id")
    ticket_start_p.add_argument(
        "--foreground",
        dest="ticket_foreground",
        action="store_true",
        help="run the pre-work sweep synchronously instead of backgrounding it",
    )
    ticket_start_p.add_argument(
        "--steal",
        dest="ticket_steal",
        action="store_true",
        help="override a refusal caused by another worktree's live lease "
        "(T-0835); invalidates that worktree's lease for close/land",
    )

    ticket_sweep_p = ticket_sub.add_parser(
        "sweep", help="re-record the pre-work sweep (after widening scope)"
    )
    ticket_sweep_p.add_argument("ticket_id", metavar="id")

    ticket_reconcile_p = ticket_sub.add_parser(
        "reconcile",
        help="heal ticket<->worktree binding drift (T-0476): stale "
        "in-progress holds with no live lease, and orphan live worktrees "
        "with no lease at all",
    )
    ticket_reconcile_p.add_argument(
        "--apply",
        dest="ticket_reconcile_apply",
        action="store_true",
        help="actually requeue stale holds (default: dry-run report only)",
    )
    ticket_reconcile_p.add_argument(
        "--remove-orphans",
        dest="ticket_reconcile_remove_orphans",
        action="store_true",
        help="with --apply, also `git worktree remove` orphan worktrees "
        "(a strictly more destructive action, gated separately)",
    )

    ticket_migrate_p = ticket_sub.add_parser(
        "migrate", help="collapse legacy tickets/*.md into a single tickets.md ledger"
    )
    ticket_renumber_p = _add_ticket_renumber_parser(ticket_sub)
    ticket_land_p = _add_ticket_land_parser(ticket_sub)
    ticket_merge_driver_p = _add_ticket_merge_driver_parser(ticket_sub)
    return [
        ticket_plan_p,
        ticket_requeue_p,
        ticket_start_p,
        ticket_sweep_p,
        ticket_reconcile_p,
        ticket_migrate_p,
        ticket_renumber_p,
        ticket_land_p,
        ticket_merge_driver_p,
    ]


# frob:ticket T-0323
def _add_ticket_merge_driver_parser(ticket_sub):
    """Register `frob ticket merge-driver %O %A %B`, the git merge-driver
    entry point (docs/modules/tickets.md#git-merge-driver): git invokes
    this with base/ours/theirs temp file paths and expects the splice
    result written back into `ours` (%A)."""
    ticket_merge_driver_p = ticket_sub.add_parser(
        "merge-driver",
        help="git merge driver for tickets.md -- splices base/ours/theirs "
        "via splice_ledger instead of a line-level textual merge",
    )
    ticket_merge_driver_p.add_argument("ticket_merge_base", metavar="%O")
    ticket_merge_driver_p.add_argument("ticket_merge_ours", metavar="%A")
    ticket_merge_driver_p.add_argument("ticket_merge_theirs", metavar="%B")
    return ticket_merge_driver_p


def _add_ticket_renumber_parser(ticket_sub):
    """Register `frob ticket renumber` and return its subparser."""
    ticket_renumber_p = ticket_sub.add_parser(
        "renumber",
        help="rewrite one ticket's id everywhere (with <old> <new>), or "
        "reassign every id to a contiguous T-0001.. sequence (no args)",
    )
    ticket_renumber_p.add_argument(
        "ticket_old_id", metavar="old", nargs="?", default=None
    )
    ticket_renumber_p.add_argument(
        "ticket_new_id", metavar="new", nargs="?", default=None
    )
    ticket_renumber_p.add_argument(
        "--dry-run",
        dest="ticket_dry_run",
        action="store_true",
        help="report what renumber <old> <new> would change without writing",
    )
    return ticket_renumber_p


def _add_ticket_land_parser(ticket_sub):
    """Register `frob ticket land` and return its subparser."""
    ticket_land_p = ticket_sub.add_parser(
        "land",
        help="one-command landing: merge-check-splice-close-commit "
        "a ticket's worktree onto this checkout",
    )
    ticket_land_p.add_argument("ticket_id", metavar="id")
    ticket_land_p.add_argument(
        "--worktree",
        dest="ticket_worktree",
        metavar="PATH",
        required=True,
        help="path to the worktree checked out to the ticket's branch",
    )
    ticket_land_p.add_argument(
        "--dry-run",
        dest="ticket_dry_run",
        action="store_true",
        help="run every check and git operation landing would, then unwind it",
    )
    ticket_land_p.add_argument(
        "--skip-mutation-evidence",
        dest="ticket_skip_mutation_evidence",
        action="store_true",
        help=(
            "T-0755 escape hatch: do not let a TEST016 confirmatory-only-"
            "evidence finding refuse the land (the check still runs and "
            "logs its findings at WARNING; this only stops it from "
            "blocking). Use for a genuine false positive, not to wave "
            "through real confirmatory evidence."
        ),
    )
    ticket_land_p.add_argument(
        "--push",
        dest="ticket_land_push",
        action="store_true",
        help=(
            "T-0631: after landing succeeds (every land verification -- "
            "precheck, D-05 re-verification, TICK005 regression sweep, "
            "completeness assertion -- passed and the final commit is "
            "made), push root's current branch to its upstream remote. "
            "Never pushes on a dry run, and never pushes if landing "
            "itself failed."
        ),
    )
    return ticket_land_p


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
    return ticket_done_report_p


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


def _add_ticket_closeout_parsers(ticket_sub) -> list:
    """Register the ticket closeout subcommands: attach/block/close/
    reverify/fail/evidence/done-report/scope/priority/kind/component/
    label/review/sprint/tier."""
    return (
        _add_ticket_attach_and_lifecycle_end_parsers(ticket_sub)
        + _add_ticket_fail_evidence_archive_parsers(ticket_sub)
        + [
            # frob:ticket T-1005
            _add_ticket_reverify_parser(ticket_sub),
            _add_ticket_done_report_parser(ticket_sub),
            _add_ticket_scope_parser(ticket_sub),
            _add_ticket_priority_parser(ticket_sub),
            _add_ticket_kind_parser(ticket_sub),
            _add_ticket_component_parser(ticket_sub),
            _add_ticket_label_parser(ticket_sub),
            _add_ticket_review_parser(ticket_sub),
            # frob:ticket T-0715
            _add_ticket_sprint_parser(ticket_sub),
            # frob:ticket T-1069
            _add_ticket_tier_parser(ticket_sub),
        ]
    )


# frob:ticket T-0030
def _add_ticket_lifecycle_parsers(ticket_sub) -> list:
    """Register the state-transition ticket subcommands (plan/start/close/...)."""
    return _add_ticket_progress_parsers(ticket_sub) + _add_ticket_closeout_parsers(
        ticket_sub
    )


# frob:ticket T-0030
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


# frob:ticket T-0030
