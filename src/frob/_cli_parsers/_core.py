# frob:waive INV006 reason="T-1076 split of __main__.py's original T-0585 waiver: this \
# module's help/docstring text carries incidental exclusivity-flavored wording \
# (argparse help strings, scope-cut prose) inherited verbatim from __main__.py, not a \
# new normative contract -- disposed as the same calibration batch, not claim-by-claim"
"""CLI parser builders: core analysis subcommands (scaffold, cycle, outline,
map, xref, parse, dup, arch, docs, exports, bind, agent, worktree).

Split out of `frob.__main__` (T-1076) purely to keep that module below the
large-file gate threshold -- no behavior change, same argparse tree.
"""

from __future__ import annotations


def _add_scaffold_parser(sub) -> None:
    """Register the `frob scaffold` subcommand and its arguments."""
    # -- scaffold ------------------------------------------------------------
    scaffold_p = sub.add_parser(
        "scaffold", help="scaffold a new project from a template"
    )
    scaffold_sub = scaffold_p.add_subparsers(dest="scaffold_command")
    scaffold_sub.add_parser("list", help="list registered project types")
    # T-0736: idempotently install/update the managed boilerplate blocks
    # (Makefile core-shim, standard .gitignore entries, worktree-lease
    # hooks) in the current repo.
    scaffold_sub.add_parser(
        "apply", help="install/update managed boilerplate blocks (T-0736)"
    )
    scaffold_new_p = scaffold_sub.add_parser("new", help="create a new project")
    scaffold_new_p.add_argument(
        "scaffold_type", metavar="type", help="project type (e.g. python-tool)"
    )
    scaffold_new_p.add_argument("scaffold_name", metavar="name", help="project name")
    scaffold_new_p.add_argument("--output", dest="scaffold_output", metavar="DIR")
    scaffold_new_p.add_argument(
        "--force",
        dest="scaffold_force",
        action="store_true",
        help="overwrite existing files",
    )

    # T-0877: `frob scaffold pool warm/lease/status`, wired onto the
    # T-0738 `frob.scaffold._pool` API -- replaces the Makefile's
    # inline-python `pool-warm`/`pool-lease`/`pool-status` shims.
    scaffold_pool_p = scaffold_sub.add_parser(
        "pool", help="worktree warm pool: warm/lease/status (T-0738/T-0877)"
    )
    scaffold_pool_sub = scaffold_pool_p.add_subparsers(dest="scaffold_pool_command")
    scaffold_pool_warm_p = scaffold_pool_sub.add_parser(
        "warm", help="fill the pool to N ready slots"
    )
    scaffold_pool_warm_p.add_argument(
        "scaffold_pool_n",
        metavar="N",
        type=int,
        nargs="?",
        default=4,
        help="number of ready slots to maintain (default 4)",
    )
    scaffold_pool_sub.add_parser(
        "lease", help="lease one ready slot, print its path, refill in background"
    )
    scaffold_pool_sub.add_parser("status", help="print the current pool manifest")


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_cycle_parser(sub) -> None:
    """Register the `frob cycle` subcommand and its arguments."""
    # -- cycle ---------------------------------------------------------------
    cycle_p = sub.add_parser("cycle", help="detect dependency cycles")
    cycle_p.add_argument("cycle_path", metavar="path")
    cycle_p.add_argument("--lang", dest="cycle_lang", choices=["python", "cpp", "c"])
    cycle_p.add_argument("--suggest", dest="cycle_suggest", action="store_true")


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_outline_parser(sub) -> None:
    """Register the `frob outline` subcommand and its arguments."""
    # -- outline -------------------------------------------------------------
    outline_p = sub.add_parser(
        "outline",
        help=(
            "[DEPRECATED, sunset 2026-10-01, see T-0580] show structural "
            "skeleton of a file (classes, functions, line numbers)"
        ),
    )
    outline_p.add_argument("outline_file", metavar="file")
    outline_p.add_argument("--json", dest="outline_json", action="store_true")
    outline_p.add_argument(
        "--all", dest="outline_all", action="store_true", help="include private symbols"
    )


# frob:ticket T-0030
def _add_map_parser(sub) -> None:
    """Register the `frob map` subcommand and its arguments."""
    # -- map -----------------------------------------------------------------
    map_p = sub.add_parser(
        "map",
        help=(
            "[DEPRECATED, sunset 2026-10-01, see T-0580] show whole-project "
            "structural map (symbols + line counts)"
        ),
    )
    map_p.add_argument("map_path", metavar="path", nargs="?", default=".")
    map_p.add_argument("--json", dest="map_json", action="store_true")
    map_p.add_argument("--depth", dest="map_depth", type=int, metavar="N")
    map_p.add_argument(
        "--all", dest="map_all", action="store_true", help="include private symbols"
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_xref_parser(sub) -> None:
    """Register the `frob xref` subcommand and its arguments."""
    # -- xref ----------------------------------------------------------------
    xref_p = sub.add_parser(
        "xref",
        help=(
            "[DEPRECATED, sunset 2026-10-01, see T-0580] find where a "
            "symbol is defined and every file that uses it"
        ),
    )
    xref_p.add_argument("xref_symbol", metavar="symbol")
    xref_p.add_argument("xref_path", metavar="path", nargs="?", default=".")
    xref_p.add_argument("--lang", dest="xref_lang", choices=["python", "cpp", "c"])
    xref_p.add_argument("--json", dest="xref_json", action="store_true")
    xref_p.add_argument(
        "--cross-file",
        dest="xref_cross_file",
        action="store_true",
        help="hide same-file usages (show only cross-file references)",
    )


# frob:ticket T-0030
_PARSE_TOOL_CHOICES = [
    "pytest",
    "ruff",
    "ty",
    "clang",
    "clang++",
    "gcc",
    "g++",
    "junit",
    "gtest",
    "catch2",
    "cargo",
    "clang-tidy",
    "valgrind",
    "tsc",
    "eslint",
]
"""Tool names accepted by `frob parse <tool>`, shared with its parser and tests."""


def _add_parse_input_args(parse_p) -> None:
    """Register `frob parse`'s tool/input/exit-code positional and option args."""
    parse_p.add_argument("parse_tool", metavar="tool", choices=_PARSE_TOOL_CHOICES)
    parse_p.add_argument(
        "parse_input", metavar="file", nargs="?", help="input file (default: stdin)"
    )
    parse_p.add_argument(
        "--exit-code",
        dest="parse_exit_code",
        type=int,
        default=0,
        metavar="N",
        help="exit code the tool returned (affects pass/fail)",
    )


def _add_parse_output_args(parse_p) -> None:
    """Register `frob parse`'s output-shaping flags (json/verbose/passthrough)."""
    parse_p.add_argument("--json", dest="parse_json", action="store_true")
    parse_p.add_argument(
        "--verbose",
        dest="parse_verbose",
        action="store_true",
        help="show passing tests and notes too",
    )
    parse_p.add_argument(
        "--passthrough",
        dest="parse_passthrough",
        action="store_true",
        help="exit non-zero if the tool failed (useful in pipelines)",
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_parse_parser(sub) -> None:
    """Register the `frob parse` subcommand and its arguments."""
    # -- parse ---------------------------------------------------------------
    parse_p = sub.add_parser(
        "parse",
        help="parse tool output (pytest/ruff/ty/clang/junit) into compact summary",
    )
    _add_parse_input_args(parse_p)
    _add_parse_output_args(parse_p)


# frob:ticket T-0030
# frob:ticket T-0192
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_dup_parser(sub) -> None:
    """Register the `frob dup` subcommand and its arguments."""
    # -- dup -----------------------------------------------------------------
    dup_p = sub.add_parser(
        "dup",
        help="detect duplicate/clone code segments (Type 1 exact, Type 2 renamed)",
    )
    dup_p.add_argument("dup_path", metavar="path", nargs="?", default=".")
    dup_p.add_argument(
        "--min-lines",
        dest="dup_min_lines",
        type=int,
        default=6,
        metavar="N",
        help="minimum function body size to consider (default: 6)",
    )
    dup_p.add_argument("--json", dest="dup_json", action="store_true")
    _add_dup_probe_argument(dup_p)


def _add_dup_probe_argument(dup_p) -> None:
    """Register `frob dup`'s `--probe` flag."""
    dup_p.add_argument(
        "--probe",
        dest="dup_probe",
        nargs=2,
        metavar=("SYMREF_A", "SYMREF_B"),
        default=[],
        help=(
            "R6: probe two symbols for observational equivalence "
            "(heuristically pure-only). WARNING: this EXECUTES the "
            "entire source file each symbol lives in via importlib "
            "(no sandbox) -- only use on symrefs from a tree you "
            "already trust. See docs/modules/dup.md's probe safety "
            "note."
        ),
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_arch_parser(sub) -> None:
    """Register the `frob arch` subcommand and its arguments."""
    # -- arch ----------------------------------------------------------------
    arch_p = sub.add_parser(
        "arch",
        help="arch analysis: long functions, god classes, coupling",
    )
    arch_p.add_argument("arch_path", metavar="path", nargs="?", default=".")
    arch_p.add_argument("--json", dest="arch_json", action="store_true")
    arch_p.add_argument(
        "--max-function-lines",
        dest="arch_max_function_lines",
        type=int,
        default=30,
        metavar="N",
    )
    arch_p.add_argument(
        "--max-class-methods",
        dest="arch_max_class_methods",
        type=int,
        default=12,
        metavar="N",
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_docs_parser(sub) -> None:
    """Register the `frob docs` subcommand and its arguments."""
    # -- docs ----------------------------------------------------------------
    docs_p = sub.add_parser(
        "docs",
        help="extract docstrings or search docs/ for a file/symbol",
    )
    docs_p.add_argument(
        "docs_path",
        metavar="path",
        nargs="?",
        default=None,
        help="file or directory to inspect (not needed with --sync-commands)",
    )
    docs_p.add_argument(
        "docs_symbol",
        metavar="symbol",
        nargs="?",
        default=None,
        help="class or function name (optional)",
    )
    docs_p.add_argument(
        "--overview",
        dest="docs_overview",
        action="store_true",
        help="show relevant docs/ headings and summaries",
    )
    docs_p.add_argument(
        "--search",
        dest="docs_search",
        metavar="QUERY",
        help=(
            "[DEPRECATED, sunset 2026-10-01, see T-0580] full-text search through docs/"
        ),
    )
    docs_p.add_argument("--json", dest="docs_json", action="store_true")
    docs_p.add_argument(
        "--sync-commands",
        dest="docs_sync_commands",
        action="store_true",
        help=(
            "regenerate docs/modules/cli.md's generated command table "
            "from the live argparse registry (T-1011)"
        ),
    )


# frob:ticket T-0030
def _add_exports_parser(sub) -> None:
    """Register the `frob exports` subcommand and its arguments."""
    # -- exports -------------------------------------------------------------
    exports_p = sub.add_parser(
        "exports",
        help="generate __init__.py from public symbols in a package directory",
    )
    exports_p.add_argument("exports_path", metavar="path")
    exports_p.add_argument(
        "--all",
        dest="exports_all",
        action="store_true",
        help="include private symbols",
    )
    exports_p.add_argument(
        "--exclude",
        dest="exports_exclude",
        metavar="MODULE",
        action="append",
        default=[],
        help="module name to exclude (repeatable)",
    )
    exports_p.add_argument("--json", dest="exports_json", action="store_true")
    exports_p.add_argument(
        "--write",
        dest="exports_write",
        action="store_true",
        help="write generated content to <path>/__init__.py instead of printing",
    )
    # frob:ticket T-0876
    exports_p.add_argument(
        "--consumers",
        dest="exports_consumers",
        metavar="SYMBOL",
        help=(
            "look up who imports SYMBOL under <path> instead of listing "
            "package exports (frob.exports.exports_consumers, T-0858)"
        ),
    )
    # frob:ticket T-0876
    exports_p.add_argument(
        "--lang",
        dest="exports_lang",
        choices=["python", "cpp", "c"],
        help="language override for --consumers (default: auto-detect)",
    )


# frob:ticket T-0030
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_bind_parser(sub) -> None:
    """Register the `frob bind` subcommand and its arguments."""
    # -- bind ----------------------------------------------------------------
    bind_p = sub.add_parser(
        "bind",
        help="verify binding declarations match source signatures",
    )
    bind_p.add_argument("bind_path", metavar="path", help="project root to scan")
    bind_p.add_argument(
        "--list-bindings",
        dest="bind_list_bindings",
        action="store_true",
        help="list all BIND declarations",
    )
    bind_p.add_argument(
        "--list-sources",
        dest="bind_list_sources",
        action="store_true",
        help="list all detected source signatures",
    )
    bind_p.add_argument("--json", dest="bind_json", action="store_true")


# frob:ticket T-0574
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_agent_parser(sub) -> None:
    """Register the `frob agent` subcommand tree for `--help` discovery
    only -- actual dispatch bypasses this parser entirely (see `_dispatch`
    below and `frob.app.agent_runner`'s module docstring), mirroring
    `bind`'s own precedent."""
    agent_p = sub.add_parser(
        "agent",
        help="print/export the dispatched-agent guard env (T-0574)",
    )
    agent_sub = agent_p.add_subparsers(dest="agent_command")
    agent_env_p = agent_sub.add_parser(
        "env", help="print FROB_WORKTREE/FROB_AGENT export lines for a worktree"
    )
    agent_env_p.add_argument(
        "agent_env_path",
        metavar="path",
        nargs="?",
        default=".",
        help="worktree path to resolve (default: cwd)",
    )


# frob:ticket T-0836
# frob:waive DEAD001 reason="genuinely called directly from src/frob/__main__.py's \
# argparse dispatch-table wiring, but the best-effort callgraph (frob.graph.callgraph) \
# does not trace this cross-package private import -- same class of gap as this repo's \
# other cross-package DEAD001 waivers (T-1024 precedent)"
def _add_worktree_parser(sub) -> None:
    """Register the `frob worktree` subcommand tree for `--help` discovery
    only -- actual dispatch bypasses this parser entirely (see `_dispatch`
    below and `frob.app.worktree_runner`'s module docstring), mirroring
    `bind`/`agent`'s own precedent."""
    worktree_p = sub.add_parser(
        "worktree",
        help="manage dispatched-agent git worktrees (T-0836)",
    )
    worktree_sub = worktree_p.add_subparsers(dest="worktree_command")
    worktree_sweep_p = worktree_sub.add_parser(
        "sweep", help="lease-aware stale-worktree cleanup"
    )
    worktree_sweep_p.add_argument(
        "worktree_sweep_path",
        metavar="path",
        nargs="?",
        default=".",
        help="repo root to scan (default: cwd)",
    )
    worktree_sweep_p.add_argument(
        "--dry-run",
        dest="worktree_sweep_dry_run",
        action="store_true",
        help="print verdicts without removing anything",
    )
    worktree_sweep_p.add_argument(
        "--min-age",
        dest="worktree_sweep_min_age_hours",
        type=float,
        default=None,
        metavar="HOURS",
        help="skip worktrees whose HEAD commit is newer than this many hours",
    )
