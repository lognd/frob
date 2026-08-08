# frob:ticket T-1569
"""CLI parser builder for the `frob ops` verb group (T-1569): regroups the
release/fleet/infra-plumbing porcelain (`release`/`natives`/`doctor`/
`clean`/`fleet`/`deploy`/`scaffold`/`gitlog`/`stats`) under one intent-
named subcommand instead of nine top-level entries, per the `docs/design/
cli-regrouping.md` taxonomy and the `frob explore`/`frob quality`/`frob
design` precedent (T-1238/T-1567/T-1568). Every member's standalone
top-level form keeps working unchanged -- this is a second entry point
onto the same argument dests (reusing each member's own `_populate_*`/
`_add_*_sub_parser` helper so the flag list is declared exactly once),
not a replacement."""

from __future__ import annotations

import argparse

from frob._cli_parsers._core import _populate_scaffold_actions
from frob._cli_parsers._misc import (
    _DEPLOY_EPILOG,
    _add_deploy_audit_parser,
    _add_deploy_generate_parser,
    _populate_clean_args,
    _populate_doctor_args,
    _populate_natives_actions,
    _populate_release_actions,
    _populate_stats_args,
)
from frob._cli_parsers._reporting import (
    _populate_fleet_actions,
    _populate_gitlog_args,
)


# frob:ticket T-1569
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_ops_parser(sub) -> None:
    """Register the `frob ops` subcommand group and its nine subcommands
    (`release`, `natives`, `doctor`, `clean`, `fleet`, `deploy`,
    `scaffold`, `gitlog`, `stats`), each reusing the same `AppConfig`
    dests as its standalone top-level counterpart so `ops_runner.run` can
    delegate straight into the existing runner logic."""
    ops_p = sub.add_parser(
        "ops",
        help="release/fleet/infra plumbing: release/natives/doctor/clean/"
        "fleet/deploy/scaffold/gitlog/stats grouped under one verb (T-1569)",
    )
    ops_sub = ops_p.add_subparsers(dest="ops_command")

    release_p = ops_sub.add_parser(
        "release", help="mechanical semver from the public-API graph (REL001)"
    )
    release_sub = release_p.add_subparsers(dest="release_command")
    _populate_release_actions(release_sub)

    natives_p = ops_sub.add_parser(
        "natives",
        help="build declared [[native]] crates (T-0864: frob-owned "
        "maturin develop, shared CARGO_TARGET_DIR)",
    )
    natives_sub = natives_p.add_subparsers(dest="natives_command")
    _populate_natives_actions(natives_sub)

    doctor_p = ops_sub.add_parser(
        "doctor",
        help="verify native extensions (frob_core, strata_core) are installed",
    )
    _populate_doctor_args(doctor_p)

    clean_p = ops_sub.add_parser(
        "clean",
        help="remove build/test/cache artifacts (tiered, dry-run by default)",
    )
    _populate_clean_args(clean_p)

    fleet_p = ops_sub.add_parser(
        "fleet",
        help="cross-repo status, gate rollup, and ticket routing over a "
        "fleet.toml manifest of sibling repos (T-0573)",
    )
    fleet_sub = fleet_p.add_subparsers(dest="fleet_command")
    _populate_fleet_actions(fleet_sub)

    deploy_p = ops_sub.add_parser(
        "deploy",
        help="compile std.host manifests into install/status/uninstall bash",
        epilog=_DEPLOY_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    deploy_sub = deploy_p.add_subparsers(dest="deploy_command")
    _add_deploy_generate_parser(deploy_sub)
    _add_deploy_audit_parser(deploy_sub)

    scaffold_p = ops_sub.add_parser(
        "scaffold", help="scaffold a new project from a template"
    )
    scaffold_sub = scaffold_p.add_subparsers(dest="scaffold_command")
    _populate_scaffold_actions(scaffold_sub)

    gitlog_p = ops_sub.add_parser(
        "gitlog",
        help="summarize git history by type/granularity (conventional commits)",
    )
    _populate_gitlog_args(gitlog_p)

    stats_p = ops_sub.add_parser(
        "stats", help="delivery measurement: queue health + commit cadence"
    )
    _populate_stats_args(stats_p)
