"""CLI wiring for `frob worktree sweep` (T-0836): lease-aware stale-
worktree cleanup.

Wired the same way `frob agent`/`frob bind` are (see `frob.app.
agent_runner`'s module docstring): `run(argv)` takes the raw sub-argv and
owns its own parser, bypassing the `AppConfig`/`Subcommand` dispatch table
entirely -- `frob worktree` has no ticket/graph state to load and no
reason to route through `App`, matching that precedent exactly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from frob.logging import get_logger
from frob.render import Renderer
from frob.tickets._leases import (
    LeaseError,
    force_release_lease,
    read_all_leases,
    release_orphaned_lease,
    remove_worktree,
    sweep_worktrees,
)

_log = get_logger(__name__)


def _build_worktree_parser() -> argparse.ArgumentParser:
    """Argument parser for `frob worktree`."""
    p = argparse.ArgumentParser(
        prog="frob worktree",
        description="Manage dispatched-agent git worktrees",
    )
    worktree_sub = p.add_subparsers(dest="worktree_command")
    sweep_p = worktree_sub.add_parser(
        "sweep",
        help="lease-aware stale-worktree cleanup (T-0836)",
    )
    sweep_p.add_argument(
        "path",
        nargs="?",
        default=".",
        help="repo root to scan (default: cwd)",
    )
    sweep_p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="print verdicts without removing anything",
    )
    sweep_p.add_argument(
        "--min-age",
        dest="min_age_hours",
        type=float,
        default=None,
        metavar="HOURS",
        help="skip worktrees whose HEAD commit is newer than this many hours",
    )
    # frob:ticket T-1739
    sweep_p.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help=(
            "T-1739: override the kept:live liveness gate (a process "
            "cwd'd into the worktree) for a worktree confirmed genuinely "
            "wedged -- the process scan cannot always prove a pid is "
            "dead. Has no effect on kept:dirty/kept:age; refuse-by-"
            "default is the point of this flag existing at all, use it "
            "narrowly."
        ),
    )
    # frob:ticket T-1779
    remove_p = worktree_sub.add_parser(
        "remove",
        help="safe single-worktree removal with T-1739's liveness check (T-1779)",
    )
    remove_p.add_argument("path", help="the worktree to remove")
    remove_p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="print the verdict without removing anything",
    )
    remove_p.add_argument(
        "--force",
        dest="force",
        action="store_true",
        help=(
            "T-1739: override the kept:live liveness gate for a worktree "
            "confirmed genuinely wedged -- same narrow-use posture as "
            "`sweep --force`"
        ),
    )
    # frob:ticket T-1789
    release_lease_p = worktree_sub.add_parser(
        "release-lease",
        help=(
            "release ONE ticket's cross-worktree lease, but only if it is "
            "confirmed orphaned -- its recorded worktree path no longer "
            "exists (T-1779 finding 7)"
        ),
    )
    release_lease_p.add_argument("ticket_id", metavar="id")
    return p


# frob:ticket T-1739
def _run_sweep(
    path: str, *, dry_run: bool, min_age_hours: float | None, force: bool = False
) -> None:
    """`frob worktree sweep [path]`: enumerate agent worktrees registered
    under `path`'s repository (default cwd), decide removed/kept per
    worktree via `sweep_worktrees` (T-1739: live process, then clean + no
    live lease, then age), and print one verdict line per worktree plus a
    summary count. Exits 1 with a logged error if `path` does not resolve
    to a git repository or `git worktree list` itself fails."""
    result = sweep_worktrees(
        Path(path).resolve(),
        min_age_hours=min_age_hours,
        dry_run=dry_run,
        force=force,
    )
    if result.is_err:
        _log.error("frob worktree sweep: %s (%s)", result.danger_err.value, path)
        sys.exit(1)
    verdicts = result.danger_ok
    renderer = Renderer.for_stream(sys.stdout)
    counts = {
        "removed": 0,
        "kept:live": 0,
        "kept:lease": 0,
        "kept:dirty": 0,
        "kept:age": 0,
    }
    for verdict in verdicts:
        counts[verdict.verdict] = counts.get(verdict.verdict, 0) + 1
        if verdict.detail:
            renderer.line(f"{verdict.verdict}({verdict.detail}) {verdict.path}")
        else:
            renderer.line(f"{verdict.verdict} {verdict.path}")
    renderer.line(
        f"swept {len(verdicts)} worktree(s): "
        f"{counts['removed']} removed, "
        f"{counts['kept:live']} kept:live, "
        f"{counts['kept:lease']} kept:lease, "
        f"{counts['kept:dirty']} kept:dirty, "
        f"{counts['kept:age']} kept:age"
    )


# frob:ticket T-1779
def _run_remove(path: str, *, dry_run: bool, force: bool) -> None:
    """`frob worktree remove PATH` (T-1779): the safe single-worktree
    twin of `sweep`, reachable without enumerating/deciding on every
    OTHER worktree first -- the incident this closes (`git worktree
    remove` deleting a live agent's checkout, T-1779's incident 4) needs
    a path that is EASIER to reach than the raw command, not merely a
    safer one. `root` is resolved from cwd (any worktree of a repository
    can target `git worktree remove` at any other, since both share the
    same underlying repository) -- `PATH`, not `root`, is the worktree
    being acted on. Exits 1 with a logged error if `PATH` is not a
    git-registered `.claude/worktrees/` agent worktree of this
    repository, or if the T-1739 liveness/dirty/lease gates keep it."""
    root = Path(".").resolve()
    result = remove_worktree(root, Path(path), dry_run=dry_run, force=force)
    if result.is_err:
        _log.error("frob worktree remove: %s (%s)", result.danger_err.value, path)
        sys.exit(1)
    verdict = result.danger_ok
    renderer = Renderer.for_stream(sys.stdout)
    if verdict.detail:
        renderer.line(f"{verdict.verdict}({verdict.detail}) {verdict.path}")
    else:
        renderer.line(f"{verdict.verdict} {verdict.path}")
    if verdict.verdict != "removed":
        sys.exit(1)


# frob:ticket T-2175
def _lease_scope_diverged_from_ledger(root: Path, ticket_id: str) -> bool:
    """T-2175: `True` iff `ticket_id` HAS a recorded lease, that lease's
    own `scope` shares NOTHING at all with `ticket_id`'s CURRENT declared
    scope in `root`'s ledger -- a fifth staleness shape T-1806/T-2048's
    four (path-gone/ticket-gone/ticket-terminal/holder-dead, all in
    `frob.tickets._leases.lease_staleness_reason`) do not cover, and the
    exact real-incident shape this ticket was filed from: an id that
    briefly belonged to a DIFFERENT ticket before being renumbered
    (T-2114 -> T-2140), leaving a lease recorded under the old identity's
    scope pointing at a worktree that still exists, for a ticket id that
    still resolves in the ledger (so path-gone/ticket-gone never fire)
    and whose ticket may not even be terminal (so ticket-terminal never
    fires either) -- and freshly enough recorded that `holder-dead`'s TTL
    gate cannot fire regardless of how long the underlying worktree has
    actually been idle.

    A ticket's own lease is written once, at `IN_PROGRESS` entry, from the
    SAME `scope` the ledger records at that moment, and only ever GROWS
    from there (`frob ticket scope --add`) -- never shrinks to something
    wholly unrelated. A COMPLETE disjunction between the two is therefore
    strong, conservative evidence that the lease on disk was never
    written for the ticket now living under this id at all, not a normal
    in-progress ticket whose scope merely narrowed or grew since start.
    Deliberately does NOT fire on a PARTIAL overlap (a ticket's scope
    narrowing via `--remove`, or growing via `--add`, both still leave
    real overlap) -- only total disjunction, to stay strictly narrower
    than (never a substitute for) `lease_staleness_reason`'s own four
    checks, and to never treat an ordinary live ticket's scope change as
    staleness.

    `False` on any lookup failure (no lease recorded, ledger unreadable,
    ticket absent from the ledger) -- this function adds one NEW positive
    signal on top of the existing checks, it never itself decides
    "unmeasurable means stale"."""
    leases = read_all_leases(root)
    record = next((r for r in leases if r.ticket_id == ticket_id), None)
    if record is None:
        return False
    from frob.tickets._archive import load_queue

    queue = load_queue(root)
    if queue.is_err:
        return False
    ticket = queue.danger_ok.tickets.get(ticket_id)
    if ticket is None:
        return False
    lease_scope = set(record.scope)
    ledger_scope = set(ticket.scope)
    if not lease_scope or not ledger_scope:
        return False
    return lease_scope.isdisjoint(ledger_scope)


# frob:ticket T-1789
# frob:ticket T-1806
# frob:ticket T-2175
def _run_release_lease(ticket_id: str) -> None:
    """`frob worktree release-lease TICKET-ID` (T-1779 finding 7): the
    safe, scoped path a coordinator now has for exactly the recovery
    T-1766's ghost lease forced by hand (`rm .git/frob-leases/T-1766.json`)
    -- refuses (exit 1) unless `release_orphaned_lease` confirms the
    lease is genuinely stale, by any of `lease_staleness_reason`'s four
    shapes (T-1806/T-2048: path-gone, ticket-gone, ticket-terminal, or
    holder-dead -- not just path-gone as before), so this can never
    release a lease still pinned to a live, ticketed, occupied worktree
    by mistake.

    T-2175: when `release_orphaned_lease` refuses with `LeaseWorktreeMismatch`
    (none of those four shapes fired), this ALSO independently checks
    `_lease_scope_diverged_from_ledger` -- a fifth shape those four do not
    cover (see that function's own docstring for the real incident this
    closes) -- and force-releases via `force_release_lease` (T-1743's
    existing operator-clears-someone-else's-lease primitive, never wired
    to a CLI verb before this) when it fires. This is a genuine, freshly-
    computed positive signal, not a bypass of the existing safety check:
    every ordinary live ticket's lease scope still overlaps its own
    current ledger scope, so this can never fire for the live-worktree
    case `LeaseWorktreeMismatch` exists to protect.

    T-2175 also fixes the refusal MESSAGE itself: the old text
    unconditionally asserted three specific conditions ("its worktree
    exists, its ticket is in the ledger, and a process holds it") that
    `LeaseWorktreeMismatch` alone does not individually confirm --
    `lease_staleness_reason` returning `None` only means none of its own
    checks fired, not that every one of those three claims is true (a
    live-process claim in particular was never checked at all on this
    path). The message now names only what `LeaseWorktreeMismatch`
    actually means (none of the known staleness shapes matched) and
    points at the two real recovery paths, instead of asserting an
    unverified diagnosis.

    `root` is resolved from cwd, same convention as `frob worktree
    remove`."""
    root = Path(".").resolve()
    result = release_orphaned_lease(root, ticket_id)
    if result.is_ok:
        renderer = Renderer.for_stream(sys.stdout)
        renderer.line(f"released orphaned lease for {ticket_id}")
        return
    err = result.danger_err
    if err is LeaseError.NoLeaseForTicket:
        _log.error("frob worktree release-lease: %s has no recorded lease", ticket_id)
        sys.exit(1)
    if err is LeaseError.LeaseWorktreeMismatch and _lease_scope_diverged_from_ledger(
        root, ticket_id
    ):
        force_release_lease(root, ticket_id)
        _log.warning(
            "frob worktree release-lease: %s's lease scope shares nothing "
            "with its current ledger scope -- id-reuse/renumber residue, "
            "not a live holder; force-released via T-2175's scope-"
            "divergence check",
            ticket_id,
        )
        renderer = Renderer.for_stream(sys.stdout)
        renderer.line(f"released orphaned lease for {ticket_id}")
        return
    if err is LeaseError.LeaseWorktreeMismatch:
        _log.error(
            "frob worktree release-lease: %s's lease matched none of the "
            "known staleness shapes (path-gone, ticket-gone, ticket-"
            "terminal, holder-dead, scope-diverged) -- this does not by "
            "itself confirm the worktree is live or a process holds it, "
            "only that nothing here could yet prove it is not; if you have "
            "independently confirmed the holder is dead, use `frob "
            "worktree remove` (or the ordinary ticket-close path) instead",
            ticket_id,
        )
    else:
        _log.error("frob worktree release-lease: %s (%s)", err.value, ticket_id)
    sys.exit(1)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-1779
# frob:ticket T-1789
# frob:tests tests/test_ticket_leases.py::TestWorktreeSweepCli.test_sweep_cli_prints_verdicts_and_summary  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWorktreeRemoveCli.test_remove_cli_removes_a_clean_unleased_worktree  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWorktreeRemoveCli.test_remove_cli_exits_1_and_names_the_error_for_a_bad_path  # noqa: E501
# frob:tests \
# tests/test_ticket_leases.py::TestWorktreeRemoveCli.test_remove_cli_exits_1_when_kept
# frob:tests tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli.test_release_lease_cli_releases_an_orphaned_lease  # noqa: E501
# frob:tests tests/test_ticket_leases.py::TestWorktreeReleaseLeaseCli.test_release_lease_cli_exits_1_for_a_live_worktree  # noqa: E501
def run(argv: list[str]) -> None:
    """`frob worktree <subcommand>` entry point (T-0836), dispatched
    directly by `__main__._dispatch` the same way `frob agent`/`frob
    bind` are. The implemented subcommand surface is `sweep` (bulk) and
    `remove` (single-worktree, T-1779); an unrecognized/missing
    subcommand falls through to argparse's own usage error."""
    parser = _build_worktree_parser()
    args = parser.parse_args(argv)
    if args.worktree_command == "sweep":
        _run_sweep(
            args.path,
            dry_run=args.dry_run,
            min_age_hours=args.min_age_hours,
            force=args.force,
        )
        return
    if args.worktree_command == "remove":
        _run_remove(args.path, dry_run=args.dry_run, force=args.force)
        return
    if args.worktree_command == "release-lease":
        _run_release_lease(args.ticket_id)
        return
    parser.print_help(sys.stderr)
    sys.exit(1)


__all__ = ["run"]
