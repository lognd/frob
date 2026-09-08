"""`frob release publish`/`frob release status` CLI wiring (T-2242/T-4301).

Dispatched directly from `frob.__main__._dispatch`, mirroring `bind`/
`agent`/`worktree`/`sync-skills`'s own precedent (T-0355/T-0574/T-0836/
T-2241): these subcommands do not extend `frob.app.release_runner`'s
existing `stamp`/`check`/`sync` `AppConfig`-routed dispatch, since T-2242's
own declared scope (`src/frob/release/**`, `scripts/bump_version.py`,
`Makefile`, docs, tests) deliberately does not include `src/frob/app/
release_runner.py` or `src/frob/_cli_parsers/**` -- adding a verb
through that existing dispatch table would need touching both.
`add_release_publish_parser`/`run_release_publish_command` (and, for
`status`, `add_release_status_parser`/`run_release_status_command`) follow
the exact shape `frob.refactor._cli.add_refactor_parser`/`run_refactor_
command` already established for a subcommand dispatched this way.

`status` (T-4301) is the single-command answer to "what will publish, at
what version, with the bump on or off" -- today that state is spread
across `.frob-release.json` (the manifest), `pyproject.toml`'s
`[project].version` (the authoritative on-disk version) and its
`[tool.frob]` table (the per-land dev-version-bump toggle/ack, T-4184),
requiring three separate reads to assemble by hand. It also runs the same
`diff_class`/`required_version`/`satisfies` check `frob release check`
(`frob.app.release_runner._check`) already does, so a caller sees the
gate's own verdict -- BUMP REQUIRED or OK -- rather than raw fields it
would have to re-derive the verdict from itself."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from frob.render import Renderer


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
        help="frob release publish -- version bump + commit + push + build + publish",
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


# frob:ticket T-4301
# frob:tests \
# tests/test_release.py::TestAddReleaseStatusParser.test_registers_relea\
# se_status  # noqa: E501
# frob:waive COV001 reason="a frob:doc anchor here would live in \
# docs/modules/release.md, whose own SCOPE002 closure (every OTHER \
# pre-existing symbol that shared doc file already describes across \
# src/frob/release/**, plus src/frob/gates/__init__.py's REL001/REL002 \
# gates) is out of proportion to pull into this CLI-wiring ticket's \
# scope -- same posture T-1010's own COV001 waiver took for \
# docs/modules/gates.md's identical fan-out (see \
# tickets/archive/T-1881/evidence/stage1-frob-check.json); this \
# function's own docstring is the authoritative description"  # noqa: E501
def add_release_status_parser(sub: argparse._SubParsersAction) -> None:
    """Register `frob release status [path]` on an argparse subparsers
    object -- same self-contained shape as `add_release_publish_parser`
    above (its own `release` parser + `release_subcommand` subparsers),
    not shared with `publish`'s tree: each direct-dispatch path
    (`_dispatch_release_publish`/`_dispatch_release_status` in
    `frob.__main__`) only ever needs to parse its OWN verb, so keeping
    the two builders independent avoids one call's `sub.add_parser
    ("release", ...)` silently clobbering the other's already-registered
    `release` choice in the same subparsers action."""
    release_p = sub.add_parser(
        "release",
        help="frob release status -- version, dev-bump toggle/ack, and the "
        "release gate's own bump verdict, in one command (T-4301)",
    )
    release_sub = release_p.add_subparsers(dest="release_subcommand", required=True)
    status_p = release_sub.add_parser(
        "status",
        help="frob release status -- version, dev-bump toggle/ack, and the "
        "release gate's own bump verdict, in one command (T-4301)",
    )
    status_p.add_argument(
        "path", nargs="?", default=".", help="repo root (default: cwd)"
    )


# frob:ticket T-4301
# frob:tests \
# tests/test_release.py::TestRunReleaseStatusCommand.test_reports_bump_r\
# equired_when_gate_refuses  # noqa: E501
# frob:tests \
# tests/test_release.py::TestRunReleaseStatusCommand.test_reports_ok_and\
# _dev_bump_toggle_state  # noqa: E501
# frob:waive ARCH103 reason="T-0977: CLI entrypoint whose one job is \
# orchestration -- resolve the root, read the manifest/version/toggle \
# fields, compute the gate verdict, and render it; matching \
# run_release_publish_command's own ARCH103 waiver directly above for \
# the identical shape"  # noqa: E501
# frob:waive COV001 reason="a frob:doc anchor here would live in \
# docs/modules/release.md, whose own SCOPE002 closure (every OTHER \
# pre-existing symbol that shared doc file already describes across \
# src/frob/release/**, plus src/frob/gates/__init__.py's REL001/REL002 \
# gates) is out of proportion to pull into this CLI-wiring ticket's \
# scope -- same posture T-1010's own COV001 waiver took for \
# docs/modules/gates.md's identical fan-out (see \
# tickets/archive/T-1881/evidence/stage1-frob-check.json); this \
# function's own docstring is the authoritative description"  # noqa: E501
def run_release_status_command(args: argparse.Namespace) -> int:
    """Execute a parsed `frob release status [path]` invocation: print the
    authoritative version, the per-land dev-version-bump toggle and major-
    version ack (T-4184), and the release gate's own verdict (the same
    `diff_class`/`required_version`/`satisfies` computation `frob release
    check` runs, T-0562) -- one command answering "what will publish, at
    what version, with the bump on or off" instead of three separate
    reads across `.frob-release.json`, `pyproject.toml`'s `[project]`
    table, and its `[tool.frob]` table. Returns 1 (mirroring `frob release
    check`'s own exit code) when the gate's verdict is BUMP REQUIRED, else
    0 -- a status verb that cannot surface that refusal in its exit code
    is not much use to a caller scripting around it."""
    from frob.app._snapshot import load_or_build_snapshot
    from frob.release import (
        current_version,
        dev_version_bump_enabled,
        dev_version_major_ack,
        diff_class,
        load_manifest,
        required_version,
        satisfies,
    )

    root = Path(args.path).resolve()
    renderer = Renderer.for_stream(sys.stdout)

    version_result = current_version(root)
    if version_result.is_err:
        print(f"release status: {version_result.danger_err}", file=sys.stderr)
        return 1
    version = version_result.danger_ok

    bump_enabled = dev_version_bump_enabled(root)
    major_ack = dev_version_major_ack(root)
    renderer.line(f"version: {version}")
    renderer.line(
        f"dev-version bump: {'on' if bump_enabled else 'off'} "
        f"(major ack: {major_ack if major_ack else 'none'})"
    )

    manifest_result = load_manifest(root)
    if manifest_result.is_err:
        renderer.line(f"release gate: {manifest_result.danger_err} (no verdict)")
        return 1

    manifest = manifest_result.danger_ok
    bump = diff_class(manifest, load_or_build_snapshot(root, log_context="release"))
    need = required_version(manifest.version, bump)
    target = need.danger_ok if need.is_ok else "?"
    ok = need.is_ok and satisfies(version, need.danger_ok)
    renderer.line(
        f"release gate: since {manifest.version}: {bump.name.lower()} change -> "
        f"need >= {target}: {'OK' if ok else 'BUMP REQUIRED'}"
    )
    return 0 if ok else 1


# frob:ticket T-2242
# frob:doc docs/modules/release.md#frob-release-publish-t-2242
# frob:tests tests/test_release.py::TestRunReleasePublishCommand.test_dry_run_prints_the_plan_and_exits_0  # noqa: E501
# frob:tests tests/test_release.py::TestRunReleasePublishCommand.test_publish_failure_exits_nonzero  # noqa: E501
# frob:waive ARCH103 reason="T-0977: CLI entrypoint whose one job is orchestration -- resolve the root, invoke publish(), and render the outcome (error path vs dry-run vs real-run); the two decision points ARE that dispatch, matching every other CLI runner already waived under T-0977 (see app/*_runner.py)"  # noqa: E501
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
    renderer = Renderer.for_stream(sys.stdout)
    if report.dry_run:
        renderer.line(
            f"release publish --dry-run: would bump {plan.current_version} -> "
            f"{plan.new_version}"
        )
        renderer.line(f"  would commit: {', '.join(plan.files_to_commit)}")
        renderer.line("  would push, build, and publish")
    else:
        renderer.line(
            f"release publish: {plan.current_version} -> {plan.new_version}, "
            f"steps: {', '.join(report.executed_steps)}"
        )
    return 0


__all__ = [
    "add_release_publish_parser",
    "add_release_status_parser",
    "run_release_publish_command",
    "run_release_status_command",
]
