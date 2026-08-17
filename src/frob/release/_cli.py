"""`frob release publish` CLI wiring (T-2242).

Dispatched directly from `frob.__main__._dispatch`, mirroring `bind`/
`agent`/`worktree`/`sync-skills`'s own precedent (T-0355/T-0574/T-0836/
T-2241): this subcommand does not extend `frob.app.release_runner`'s
existing `stamp`/`check`/`sync` `AppConfig`-routed dispatch, since T-2242's
own declared scope (`src/frob/release/**`, `scripts/bump_version.py`,
`Makefile`, docs, tests) deliberately does not include `src/frob/app/
release_runner.py` or `src/frob/_cli_parsers/**` -- adding a `publish`
verb through that existing dispatch table would need touching both.
`add_release_publish_parser`/`run_release_publish_command` follow the
exact shape `frob.refactor._cli.add_refactor_parser`/`run_refactor_
command` already established for a subcommand dispatched this way."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


# frob:ticket T-2242
# frob:doc docs/modules/release.md#frob-release-publish-t-2242
# frob:tests \
# tests/test_release.py::TestAddReleasePublishParser.test_registers_rele\
# ase_publish_with_dry_run_flag  # noqa: E501
def add_release_publish_parser(sub: argparse._SubParsersAction) -> None:
    """Register `frob release publish [--dry-run]` on an argparse
    subparsers object -- matching every other `_add_*_parser` builder's
    shape (`src/frob/_cli_parsers/**`'s existing convention), even though
    this one is wired in from `frob.__main__._dispatch` directly rather
    than through that package (see this module's own docstring for why)."""
    release_p = sub.add_parser(
        "release",
        help="frob release publish -- version bump + commit + push + build + "
        "publish",
    )
    release_sub = release_p.add_subparsers(dest="release_subcommand", required=True)
    publish_p = release_sub.add_parser(
        "publish",
        help="bump the patch version, stamp/sync the release, commit, push, "
        "build, and publish (T-2242) -- replaces the old Makefile upload: recipe",
    )
    publish_p.add_argument(
        "path", nargs="?", default=".", help="repo root (default: cwd)"
    )
    publish_p.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="report the version bump and files this would touch/push/publish "
        "without mutating anything -- no commit, no push, no build, no publish",
    )


# frob:ticket T-2242
# frob:doc docs/modules/release.md#frob-release-publish-t-2242
# frob:tests tests/test_release.py::TestRunReleasePublishCommand.test_dry_run_prints_the_plan_and_exits_0  # noqa: E501
# frob:tests tests/test_release.py::TestRunReleasePublishCommand.test_publish_failure_exits_nonzero  # noqa: E501
def run_release_publish_command(args: argparse.Namespace) -> int:
    """Execute a parsed `frob release publish [--dry-run]` invocation and
    print the disclosed report; returns the process exit code (0 success,
    1 on any step's failure)."""
    from frob.app._snapshot import load_or_build_snapshot
    from frob.release._publish import publish

    root = Path(args.path).resolve()
    snapshot = load_or_build_snapshot(root, log_context="release publish")
    result = publish(root, snapshot, dry_run=args.dry_run)
    if result.is_err:
        print(f"release publish: {result.danger_err}", file=sys.stderr)
        return 1

    report = result.danger_ok
    plan = report.plan
    if report.dry_run:
        print(
            f"release publish --dry-run: would bump {plan.current_version} -> "
            f"{plan.new_version}"
        )
        print(f"  would commit: {', '.join(plan.files_to_commit)}")
        print("  would push, build, and publish")
    else:
        print(
            f"release publish: {plan.current_version} -> {plan.new_version}, "
            f"steps: {', '.join(report.executed_steps)}"
        )
    return 0


__all__ = ["add_release_publish_parser", "run_release_publish_command"]
