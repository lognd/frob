"""CLI parser builders: core analysis subcommands (scaffold, cycle, outline,
map, xref, parse, dup, arch, docs, exports, bind, agent, worktree).

Split out of `frob.__main__` (T-1076) purely to keep that module below the
large-file gate threshold -- no behavior change, same argparse tree.
"""

from __future__ import annotations

from frob.lang import language_for_extension, tree_sitter_extensions

# frob:doc docs/commands/xref.md#public-api
# frob:ticket T-3233
# frob:tests tests/unit/test_cli_lang_choices_drift.py::test_lang_choices_track_frob_lang_registry  # noqa: E501
_LANG_CHOICES: tuple[str, ...] = tuple(
    sorted(
        {
            lang
            for ext in tree_sitter_extensions()
            if (lang := language_for_extension(ext)) is not None
        }
    )
)
"""Every `--lang` argparse `choices` list in this module routes through
here (T-3233, T-2996's measurement) instead of each hand-typing its own
hard-coded `['python', 'cpp', 'c']` copy -- the single source of truth
is `frob.lang`'s own tree-sitter extension registry, so a new grammar
`frob.lang` gains (kotlin, csharp, cuda, zig, bash, ... T-1600-1604) is
selectable here automatically, with no CLI-layer literal to remember to
update. `tree_sitter_extensions()` (not `supported_languages()`)
deliberately excludes `.strata`: `--lang` filters `frob cycle`'s
`extract_import_edges` and `frob xref`/`frob exports --consumers`'s
tree-sitter-backed lookup, both tree-sitter-only escape hatches with no
`.strata` analogue (frob.lang's own docstrings)."""


def _add_scaffold_parser(sub) -> None:
    """Register the `frob scaffold` subcommand and its arguments."""
    # -- scaffold ------------------------------------------------------------
    scaffold_p = sub.add_parser(
        "scaffold", help="scaffold a new project from a template"
    )
    scaffold_sub = scaffold_p.add_subparsers(dest="scaffold_command")
    _populate_scaffold_actions(scaffold_sub)


# frob:ticket T-1569
def _populate_scaffold_actions(scaffold_sub) -> None:
    """Add `frob scaffold`'s `list`/`apply`/`new`/`pool` actions onto
    `scaffold_sub` -- shared by the standalone top-level parser and `frob
    ops scaffold` (T-1569) so neither duplicates the flag list."""
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
    scaffold_new_p.add_argument(
        "--output",
        dest="scaffold_output",
        metavar="DIR",
        help="parent directory to scaffold into (default: .); the project "
        "is always written to DIR/<name>, never loose into DIR (T-3271)",
    )
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
def _add_cycle_parser(sub) -> None:
    """Register the `frob cycle` subcommand and its arguments."""
    # -- cycle ---------------------------------------------------------------
    cycle_p = sub.add_parser("cycle", help="detect dependency cycles")
    _populate_cycle_args(cycle_p)


# frob:ticket T-1567
def _populate_cycle_args(cycle_p) -> None:
    """Add `frob cycle`'s arguments onto `cycle_p` -- shared by the
    standalone top-level parser and `frob quality cycle` (T-1567) so
    neither duplicates the flag list."""
    cycle_p.add_argument("cycle_path", metavar="path")
    cycle_p.add_argument("--lang", dest="cycle_lang", choices=_LANG_CHOICES)
    cycle_p.add_argument("--suggest", dest="cycle_suggest", action="store_true")


# frob:ticket T-0030
# frob:ticket T-1311
# frob:tests \
# tests/integration/test_interfaces.py::TestInterfaces.test_main_cli_dispatches \
# kind="integration"
def _add_outline_parser(sub) -> None:
    """Register the `frob outline` subcommand and its arguments."""
    # -- outline -------------------------------------------------------------
    outline_p = sub.add_parser(
        "outline",
        help=(
            "show structural skeleton of a file (classes, functions, line "
            "numbers) -- also available as `frob explore outline` (T-1238)"
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
            "show whole-project structural map (symbols + line counts) -- "
            "also available as `frob explore map` (T-1238)"
        ),
    )
    map_p.add_argument("map_path", metavar="path", nargs="?", default=".")
    map_p.add_argument("--json", dest="map_json", action="store_true")
    map_p.add_argument("--depth", dest="map_depth", type=int, metavar="N")
    map_p.add_argument(
        "--all", dest="map_all", action="store_true", help="include private symbols"
    )


# frob:ticket T-0030
def _add_xref_parser(sub) -> None:
    """Register the `frob xref` subcommand and its arguments."""
    # -- xref ----------------------------------------------------------------
    xref_p = sub.add_parser(
        "xref",
        help=(
            "find where a symbol is defined and every file that uses it -- "
            "also available as `frob explore xref` (T-1238)"
        ),
    )
    xref_p.add_argument("xref_symbol", metavar="symbol")
    xref_p.add_argument("xref_path", metavar="path", nargs="?", default=".")
    xref_p.add_argument("--lang", dest="xref_lang", choices=_LANG_CHOICES)
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
def _add_dup_parser(sub) -> None:
    """Register the `frob dup` subcommand and its arguments."""
    # -- dup -----------------------------------------------------------------
    dup_p = sub.add_parser(
        "dup",
        help="detect duplicate/clone code segments (Type 1 exact, Type 2 renamed)",
    )
    _populate_dup_args(dup_p)


# frob:ticket T-1567
def _populate_dup_args(dup_p) -> None:
    """Add `frob dup`'s arguments onto `dup_p` -- shared by the standalone
    top-level parser and `frob quality dup` (T-1567) so neither duplicates
    the flag list."""
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
def _add_arch_parser(sub) -> None:
    """Register the `frob arch` subcommand and its arguments."""
    # -- arch ----------------------------------------------------------------
    arch_p = sub.add_parser(
        "arch",
        help="arch analysis: long functions, god classes, coupling",
    )
    _populate_arch_args(arch_p)


# frob:ticket T-1567
def _populate_arch_args(arch_p) -> None:
    """Add `frob arch`'s arguments onto `arch_p` -- shared by the
    standalone top-level parser and `frob quality arch` (T-1567) so
    neither duplicates the flag list."""
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
def _add_docs_parser(sub) -> None:
    """Register the `frob docs` subcommand and its arguments."""
    # -- docs ----------------------------------------------------------------
    docs_p = sub.add_parser(
        "docs",
        help="extract docstrings or search docs/ for a file/symbol",
    )
    _populate_docs_args(docs_p, include_search=True)


# frob:ticket T-1568
def _populate_docs_args(docs_p, *, include_search: bool) -> None:
    """Add `frob docs`'s arguments onto `docs_p` -- shared by the
    standalone top-level parser and `frob design docs` (T-1568) so
    neither duplicates the flag list. `include_search` is `False` for
    `frob design docs` (docs/design/cli-regrouping.md: bare extract/
    `--overview` only there, `--search` stays exclusive to `frob explore
    docs-search`) and `True` everywhere else."""
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
    if include_search:
        docs_p.add_argument(
            "--search",
            dest="docs_search",
            metavar="QUERY",
            help=(
                "full-text search through docs/ -- also available as "
                "`frob explore docs-search` (T-1238)"
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
    _populate_exports_args(exports_p)


# frob:ticket T-1568
def _populate_exports_args(exports_p) -> None:
    """Add `frob exports`'s arguments onto `exports_p` -- shared by the
    standalone top-level parser and `frob design exports` (T-1568) so
    neither duplicates the flag list."""
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
    # frob:ticket T-3233
    exports_p.add_argument(
        "--lang",
        dest="exports_lang",
        choices=_LANG_CHOICES,
        help="language override for --consumers (default: auto-detect)",
    )


# frob:ticket T-0030
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
def _add_agent_parser(sub) -> None:
    """Register the `frob agent` subcommand tree for `--help` discovery
    only -- actual dispatch bypasses this parser entirely (see `_dispatch`
    below and `frob.app.agent_runner`'s module docstring), mirroring
    `bind`'s own precedent. `agent` has exactly one child (`env`), so bare
    `frob agent` dispatches straight to it at the REAL dispatch layer
    (T-4546, same flattening `_add_claude_parser`/`_add_natives_parser`
    established, T-4522); the two-word `frob agent env` spelling is kept
    working as a documented alias for one release. This tree only sets
    the default subcommand dest for `--help` rendering -- it does NOT
    mirror `env`'s own `path` positional the way `claude`/`natives`
    mirrored their optional flags: a bare positional here would collide
    with `add_subparsers`' own positional slot (argparse would try to
    match the first token as a subcommand name first). The REAL argv
    normalization lives in `frob.app.agent_runner._normalize_agent_argv`,
    which this help-only tree is never parsed through."""
    agent_p = sub.add_parser(
        "agent",
        help="print/export the dispatched-agent guard env (T-0574) -- "
        "'env' is implied: bare `frob agent` runs it (T-4546); the "
        "two-word `frob agent env` spelling still works as an alias",
        description="print/export the dispatched-agent guard env (T-0574). "
        "'env' is implied (T-4546): bare `frob agent` runs it; the "
        "two-word `frob agent env` spelling is kept working as a "
        "documented alias for one release.",
    )
    agent_sub = agent_p.add_subparsers(dest="agent_command")
    # frob:ticket T-4546
    # T-4546: `agent` wraps exactly one child (`env`) -- default the
    # dispatch dest to it so `--help` renders correctly for bare
    # `frob agent` without requiring the subparser to be invoked
    # explicitly. See the REAL dispatch flattening in
    # frob.app.agent_runner (_normalize_agent_argv) -- this parser is
    # never used to parse real argv (see this function's own docstring).
    agent_p.set_defaults(agent_command="env")
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


# frob:ticket T-4299
def _add_whereis_parser(sub) -> None:
    """Register the `frob whereis` subcommand for `--help` discovery only
    -- actual dispatch bypasses this parser entirely (see `_dispatch`
    below and `_dispatch_whereis`'s own docstring), mirroring `bind`/
    `agent`/`worktree`'s own precedent (T-4299)."""
    whereis_p = sub.add_parser(
        "whereis",
        help="print the interpreter/site-packages path of the frob "
        "ACTUALLY RUNNING this invocation (T-4299)",
    )
    # T-4303: no frob:waive WIRE001 needed here any more -- _add_whereis_
    # parser is in WIRE001's own _WIRE001_APPCONFIG_BYPASS_PARSER_FUNCS
    # exemption set (src/frob/gates/_wire.py), so this --help-only dest
    # is never flagged in the first place.
    whereis_p.add_argument(
        "--json", dest="whereis_json", action="store_true", help="emit JSON"
    )
