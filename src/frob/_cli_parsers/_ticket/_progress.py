"""CLI parser builders for the ticket state-transition/plumbing subcommands:
plan/requeue/start/work/sweep/reconcile/migrate/renumber/land/merge-driver.

Split out of `_cli_parsers/_ticket.py` (T-1270) -- no behavior change, same
argparse tree.
"""

from __future__ import annotations


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
    # frob:ticket T-1178
    ticket_requeue_p.add_argument(
        "--no-commit",
        dest="ticket_no_commit",
        action="store_true",
        help="skip T-1178's auto-commit of the requeue ledger change "
        "(parity with `new`/`drop`/`fail`'s T-1130 auto-commit)",
    )

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

    # frob:ticket T-1175
    ticket_work_p = ticket_sub.add_parser(
        "work",
        help="one-verb worktree setup: create/reuse the ticket's worktree, "
        "merge main for freshness, build natives, then start (replaces "
        "playbook section 0 steps 1-2 plus start)",
    )
    ticket_work_p.add_argument("ticket_id", metavar="id")
    ticket_work_p.add_argument(
        "--worktree",
        dest="ticket_worktree",
        metavar="PATH",
        default=None,
        help="worktree path to create/reuse (default: "
        ".claude/worktrees/<id-lowercased>)",
    )
    ticket_work_p.add_argument(
        "--foreground",
        dest="ticket_foreground",
        action="store_true",
        help="run the pre-work sweep synchronously instead of backgrounding it",
    )
    ticket_work_p.add_argument(
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
        ticket_work_p,
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
    # frob:ticket T-1369
    ticket_land_p.add_argument(
        "--allow-cross-ticket",
        dest="ticket_allow_cross_ticket",
        action="store_true",
        help=(
            "T-1355 escape hatch: do not let a CrossTicketLeakage finding "
            "refuse the land. Use when the joint landing is genuinely "
            "intentional -- a series worktree hosting several tickets on "
            "one branch, or an open epic whose umbrella scope covers its "
            "own leaf's files -- not to wave through a real sibling leak."
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
    # frob:ticket T-1175
    ticket_land_p.add_argument(
        "--finish",
        dest="ticket_land_finish",
        action="store_true",
        help=(
            "T-1175: after a real (non-dry-run) land verifies clean "
            "(commit is an ancestor of main and the ticket's state on "
            "main is done/dropped), `git worktree remove` --worktree. "
            "Never removes on a dry run, a failed land, or a failed "
            "verify -- the worktree branch is always the recovery path "
            "(playbook section 12b) unless the land is proven landed."
        ),
    )
    return ticket_land_p
