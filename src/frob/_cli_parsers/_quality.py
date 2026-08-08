# frob:ticket T-1567
"""CLI parser builder for the `frob quality` verb group (T-1567): regroups
the correctness/hygiene-gate porcelain (`check`/`test`/`dup`/`arch`/`bind`/
`cycle`/`mutate`/`perf`) under one intent-named subcommand instead of eight
top-level entries, per the `docs/design/cli-regrouping.md` taxonomy and the
`frob explore` precedent (T-1238). Every member's standalone top-level form
keeps working unchanged -- this is a second entry point onto the same
argument dests (reusing each member's own `_populate_*_args`/`_add_*_sub_
parser` helper so the flag list is declared exactly once), not a
replacement. `bind` is the one exception: it is dispatched directly by
`frob.__main__._dispatch` before the full parser is even built (mirroring
`bind`'s own top-level special case, T-0355) since `bind_runner.run` takes
raw argv rather than an `AppConfig` -- this module still registers a `bind`
subparser so `frob quality --help`/`frob quality bind --help` discover it,
matching the `agent`/`worktree` precedent for a dispatch-bypassed entry."""

from __future__ import annotations

from frob._cli_parsers._check import (
    _add_check_scope_args,
    _add_check_selection_args,
    _add_check_skip_args,
)
from frob._cli_parsers._core import (
    _populate_arch_args,
    _populate_cycle_args,
    _populate_dup_args,
)
from frob._cli_parsers._misc import (
    _add_perf_collect_parser,
    _add_perf_heat_parser,
    _add_perf_hot_parser,
    _add_perf_profile_parser,
    _populate_mutate_args,
    _populate_test_args,
)


# frob:ticket T-1567
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_quality_parser(sub) -> None:
    """Register the `frob quality` subcommand group and its eight
    subcommands (`check`, `test`, `dup`, `arch`, `bind`, `cycle`, `mutate`,
    `perf`), each reusing the same `AppConfig` dests as its standalone
    top-level counterpart so `quality_runner.run` can delegate straight
    into the existing runner logic."""
    quality_p = sub.add_parser(
        "quality",
        help="correctness/hygiene gates: check/test/dup/arch/bind/cycle/"
        "mutate/perf grouped under one verb (T-1567)",
    )
    quality_sub = quality_p.add_subparsers(dest="quality_command")

    check_p = quality_sub.add_parser(
        "check",
        help=(
            "aggregate quality gate: ruff, ty, frob cycle/dup/arch/bind/exports; "
            "errors first, easy to hand to subagents"
        ),
    )
    _add_check_scope_args(check_p)
    _add_check_skip_args(check_p)
    _add_check_selection_args(check_p)

    test_p = quality_sub.add_parser(
        "test", help="select and run tests for the touched set (or --all)"
    )
    _populate_test_args(test_p)

    dup_p = quality_sub.add_parser(
        "dup",
        help="detect duplicate/clone code segments (Type 1 exact, Type 2 renamed)",
    )
    _populate_dup_args(dup_p)

    arch_p = quality_sub.add_parser(
        "arch",
        help="arch analysis: long functions, god classes, coupling",
    )
    _populate_arch_args(arch_p)

    bind_p = quality_sub.add_parser(
        "bind",
        help="verify binding declarations match source signatures -- "
        "dispatch bypasses this parser (see frob.__main__._dispatch), "
        "mirroring bind's own top-level precedent",
    )
    bind_p.add_argument("bind_path", metavar="path", help="project root to scan")
    # frob:waive WIRE001 follow_up="T-1820" reason="dispatch bypasses \
    # AppConfig entirely (frob.__main__._dispatch special-cases 'quality bind' before \
    # the parser tree is even consulted, T-1567), same as this file's top-level bind_p \
    # precedent in _core.py -- these dests exist for --help discovery only and are \
    # never read from a built AppConfig; the follow_up ticket records this as a \
    # permanent, by-design gap (WIRE002 requires a real ticket id outside tests/ trees)"
    bind_p.add_argument(
        "--list-bindings", dest="bind_list_bindings", action="store_true"
    )
    # frob:waive WIRE001 follow_up="T-1820" reason="dispatch bypasses \
    # AppConfig entirely (frob.__main__._dispatch special-cases 'quality bind' before \
    # the parser tree is even consulted, T-1567), same as this file's top-level bind_p \
    # precedent in _core.py -- these dests exist for --help discovery only and are \
    # never read from a built AppConfig; the follow_up ticket records this as a \
    # permanent, by-design gap (WIRE002 requires a real ticket id outside tests/ trees)"
    bind_p.add_argument("--list-sources", dest="bind_list_sources", action="store_true")
    # frob:waive WIRE001 follow_up="T-1820" reason="dispatch bypasses \
    # AppConfig entirely (frob.__main__._dispatch special-cases 'quality bind' before \
    # the parser tree is even consulted, T-1567), same as this file's top-level bind_p \
    # precedent in _core.py -- these dests exist for --help discovery only and are \
    # never read from a built AppConfig; the follow_up ticket records this as a \
    # permanent, by-design gap (WIRE002 requires a real ticket id outside tests/ trees)"
    bind_p.add_argument("--json", dest="bind_json", action="store_true")

    cycle_p = quality_sub.add_parser("cycle", help="detect dependency cycles")
    _populate_cycle_args(cycle_p)

    mutate_p = quality_sub.add_parser(
        "mutate", help="mutation testing: perturb a file, see which mutants survive"
    )
    _populate_mutate_args(mutate_p)

    perf_p = quality_sub.add_parser(
        "perf", help="profile a command/test suite and inspect its heat-map"
    )
    perf_sub = perf_p.add_subparsers(dest="perf_command")
    _add_perf_profile_parser(perf_sub)
    _add_perf_heat_parser(perf_sub)
    _add_perf_collect_parser(perf_sub)
    _add_perf_hot_parser(perf_sub)
