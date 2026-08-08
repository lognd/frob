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


# frob:ticket T-1789
def _run_release_lease(ticket_id: str) -> None:
    """`frob worktree release-lease TICKET-ID` (T-1779 finding 7): the
    safe, scoped path a coordinator now has for exactly the recovery
    T-1766's ghost lease forced by hand (`rm .git/frob-leases/T-1766.json`)
    -- refuses (exit 1) unless `release_orphaned_lease` confirms the
    lease's recorded worktree path is genuinely gone, so this can never
    release a lease still pinned to a live worktree by mistake. `root` is
    resolved from cwd, same convention as `frob worktree remove`."""
    root = Path(".").resolve()
    result = release_orphaned_lease(root, ticket_id)
    if result.is_err:
        err = result.danger_err
        if err is LeaseError.NoLeaseForTicket:
            _log.error(
                "frob worktree release-lease: %s has no recorded lease", ticket_id
            )
        elif err is LeaseError.LeaseWorktreeMismatch:
            _log.error(
                "frob worktree release-lease: %s's lease is not orphaned -- "
                "its worktree still exists; use `frob worktree remove` "
                "(and the ordinary ticket-close path) instead",
                ticket_id,
            )
        else:
            _log.error("frob worktree release-lease: %s (%s)", err.value, ticket_id)
        sys.exit(1)
    renderer = Renderer.for_stream(sys.stdout)
    renderer.line(f"released orphaned lease for {ticket_id}")


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
