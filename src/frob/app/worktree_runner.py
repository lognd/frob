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
from frob.tickets._leases import sweep_worktrees

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
    return p


# frob:doc docs/modules/app.md#runners
def _run_sweep(path: str, *, dry_run: bool, min_age_hours: float | None) -> None:
    """`frob worktree sweep [path]`: enumerate agent worktrees registered
    under `path`'s repository (default cwd), decide removed/kept per
    worktree via `sweep_worktrees` (clean + no live lease, T-0836), and
    print one verdict line per worktree plus a summary count. Exits 1
    with a logged error if `path` does not resolve to a git repository or
    `git worktree list` itself fails."""
    result = sweep_worktrees(
        Path(path).resolve(), min_age_hours=min_age_hours, dry_run=dry_run
    )
    if result.is_err:
        _log.error("frob worktree sweep: %s (%s)", result.danger_err.value, path)
        sys.exit(1)
    verdicts = result.danger_ok
    renderer = Renderer.for_stream(sys.stdout)
    counts = {"removed": 0, "kept:lease": 0, "kept:dirty": 0, "kept:age": 0}
    for verdict in verdicts:
        counts[verdict.verdict] = counts.get(verdict.verdict, 0) + 1
        if verdict.verdict == "kept:lease":
            renderer.line(f"kept:lease({verdict.detail}) {verdict.path}")
        elif verdict.detail:
            renderer.line(f"{verdict.verdict}({verdict.detail}) {verdict.path}")
        else:
            renderer.line(f"{verdict.verdict} {verdict.path}")
    renderer.line(
        f"swept {len(verdicts)} worktree(s): "
        f"{counts['removed']} removed, "
        f"{counts['kept:lease']} kept:lease, "
        f"{counts['kept:dirty']} kept:dirty, "
        f"{counts['kept:age']} kept:age"
    )


# frob:doc docs/modules/app.md#runners
# frob:tests tests/test_ticket_leases.py::TestWorktreeSweepCli.test_sweep_cli_prints_verdicts_and_summary  # noqa: E501
def run(argv: list[str]) -> None:
    """`frob worktree <subcommand>` entry point (T-0836), dispatched
    directly by `__main__._dispatch` the same way `frob agent`/`frob
    bind` are. The implemented subcommand surface today is `sweep`; an
    unrecognized/missing subcommand falls through to argparse's own usage
    error."""
    parser = _build_worktree_parser()
    args = parser.parse_args(argv)
    if args.worktree_command == "sweep":
        _run_sweep(args.path, dry_run=args.dry_run, min_age_hours=args.min_age_hours)
        return
    parser.print_help(sys.stderr)
    sys.exit(1)


__all__ = ["run"]
