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
not a replacement. T-4520: `process` (T-3106) now has a flat top-level
twin (`_add_process_parser`) -- it used to be the one group-only member
with no standalone form; both builders call the shared
`_populate_process_actions` so they cannot diverge."""

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
# frob:ticket T-4520
# frob:tests tests/unit/test_app_runners_process.py::TestProcessReapParser.test_process_reap_parses_and_dispatches  # noqa: E501
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
# frob:ticket T-4690
def _add_ops_parser(sub) -> None:
    """Register the DEPRECATED `frob ops` subcommand group (T-4690, sunset
    2026-12-01: use each member's own standalone verb directly, e.g.
    `frob release`) -- suppressed from `frob --help`'s usage line;
    `App.__call__`'s shim keeps the whole group working through the
    sunset window. Its ten subcommands (`release`, `natives`, `doctor`,
    `clean`, `fleet`, `deploy`, `scaffold`, `gitlog`, `stats`, `process`)
    are unchanged -- only the group entry point itself is deprecated.
    `process` (T-3106) is the one member with no standalone top-level
    command -- `frob ops process reap` is its only form, and stays
    reachable only through this deprecated group during the sunset
    window (no independent flat `process` verb exists to redirect to)."""
    ops_p = sub.add_parser("ops", help=argparse.SUPPRESS)
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

    process_p = ops_sub.add_parser(
        "process",
        help="process/forkserver maintenance (T-3106): reap orphaned "
        "forkservers on demand",
    )
    process_sub = process_p.add_subparsers(dest="process_command")
    _populate_process_actions(process_sub)


# frob:ticket T-4520
# frob:ticket T-4520
def _populate_process_actions(process_sub) -> None:
    """Add `reap` onto `process_sub` -- shared by the `frob ops process`
    group leaf and the flat `frob process` verb (T-4520, its twin: `ops
    process reap` used to be the only form, which made the group-to-flat
    mapping non-total) so neither duplicates the flag list."""
    reap_p = process_sub.add_parser(
        "reap",
        help="SIGTERM orphaned multiprocessing.forkserver helpers on demand "
        "(T-3072's ancestry check -- never touches one parented, at any "
        "depth, to a live `frob check`; a structural no-op on Windows/macOS)",
    )
    reap_p.add_argument(
        "--json",
        dest="process_reap_json",
        action="store_true",
        help='emit {"reaped_pids": [...]} instead of a human-readable line',
    )


# frob:ticket T-4520
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_process_parser(sub) -> None:
    """Register the flat top-level `frob process` verb (T-4520): the
    standalone twin of `frob ops process` (T-3106) -- keeps the
    group-to-flat mapping total (docs/design/cli-regrouping.md's
    derivation rule) by reusing `_populate_process_actions` instead of
    redeclaring `reap`'s flags a second time."""
    process_p = sub.add_parser(
        "process",
        help="process/forkserver maintenance (T-3106): reap orphaned "
        "forkservers on demand -- also available as `frob ops process` "
        "(T-4520)",
    )
    process_sub = process_p.add_subparsers(dest="process_command")
    _populate_process_actions(process_sub)
