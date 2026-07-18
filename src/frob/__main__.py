from __future__ import annotations

import argparse
from pathlib import Path

from frob.app import App, AppConfig


# frob:ticket T-0030
# frob:ticket T-0030
def _add_scaffold_parser(sub) -> None:
    """Register the `frob scaffold` subcommand and its arguments."""
    # -- scaffold ------------------------------------------------------------
    scaffold_p = sub.add_parser(
        "scaffold", help="scaffold a new project from a template"
    )
    scaffold_sub = scaffold_p.add_subparsers(dest="scaffold_command")
    scaffold_sub.add_parser("list", help="list registered project types")
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


# frob:ticket T-0030
def _add_cycle_parser(sub) -> None:
    """Register the `frob cycle` subcommand and its arguments."""
    # -- cycle ---------------------------------------------------------------
    cycle_p = sub.add_parser("cycle", help="detect dependency cycles")
    cycle_p.add_argument("cycle_path", metavar="path")
    cycle_p.add_argument("--lang", dest="cycle_lang", choices=["python", "cpp", "c"])
    cycle_p.add_argument("--suggest", dest="cycle_suggest", action="store_true")


# frob:ticket T-0030
def _add_outline_parser(sub) -> None:
    """Register the `frob outline` subcommand and its arguments."""
    # -- outline -------------------------------------------------------------
    outline_p = sub.add_parser(
        "outline",
        help="show structural skeleton of a file (classes, functions, line numbers)",
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
        help="show whole-project structural map (symbols + line counts)",
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
        help="find where a symbol is defined and every file that uses it",
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
def _add_parse_parser(sub) -> None:
    """Register the `frob parse` subcommand and its arguments."""
    # -- parse ---------------------------------------------------------------
    parse_p = sub.add_parser(
        "parse",
        help="parse tool output (pytest/ruff/ty/clang/junit) into compact summary",
    )
    parse_p.add_argument(
        "parse_tool",
        metavar="tool",
        choices=[
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
        ],
    )
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
    dup_p.add_argument(
        "--probe",
        dest="dup_probe",
        nargs=2,
        metavar=("SYMREF_A", "SYMREF_B"),
        default=[],
        help="R6: probe two symbols for observational equivalence (pure only)",
    )


# frob:ticket T-0030
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
def _add_docs_parser(sub) -> None:
    """Register the `frob docs` subcommand and its arguments."""
    # -- docs ----------------------------------------------------------------
    docs_p = sub.add_parser(
        "docs",
        help="extract docstrings or search docs/ for a file/symbol",
    )
    docs_p.add_argument(
        "docs_path", metavar="path", help="file or directory to inspect"
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
        help="full-text search through docs/",
    )
    docs_p.add_argument("--json", dest="docs_json", action="store_true")


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


# frob:ticket T-0030
# frob:ticket T-0030
def _add_check_skip_args(check_p) -> None:
    """Register `frob check`'s per-language stage-skip flags."""
    # Python-specific
    check_p.add_argument("--skip-ruff", dest="check_skip_ruff", action="store_true")
    check_p.add_argument("--skip-ty", dest="check_skip_ty", action="store_true")
    check_p.add_argument("--skip-arch", dest="check_skip_arch", action="store_true")
    check_p.add_argument("--skip-cycle", dest="check_skip_cycle", action="store_true")
    check_p.add_argument("--skip-dup", dest="check_skip_dup", action="store_true")
    check_p.add_argument("--skip-bind", dest="check_skip_bind", action="store_true")
    check_p.add_argument(
        "--skip-exports", dest="check_skip_exports", action="store_true"
    )
    check_p.add_argument("--skip-gates", dest="check_skip_gates", action="store_true")
    # C++ specific
    check_p.add_argument("--build-dir", dest="check_build_dir", metavar="DIR")
    check_p.add_argument("--skip-build", dest="check_skip_build", action="store_true")
    check_p.add_argument(
        "--skip-clang-tidy", dest="check_skip_clang_tidy", action="store_true"
    )
    check_p.add_argument(
        "--skip-clang-format", dest="check_skip_clang_format", action="store_true"
    )
    # Rust specific
    check_p.add_argument(
        "--skip-cargo-check", dest="check_skip_cargo_check", action="store_true"
    )
    check_p.add_argument("--skip-clippy", dest="check_skip_clippy", action="store_true")
    check_p.add_argument("--skip-fmt", dest="check_skip_fmt", action="store_true")
    # TypeScript specific
    check_p.add_argument("--skip-tsc", dest="check_skip_tsc", action="store_true")
    check_p.add_argument("--skip-eslint", dest="check_skip_eslint", action="store_true")
    check_p.add_argument(
        "--skip-prettier", dest="check_skip_prettier", action="store_true"
    )


# frob:ticket T-0030
def _add_check_parser(sub) -> None:
    """Register the `frob check` subcommand and its arguments."""
    # -- check ---------------------------------------------------------------
    check_p = sub.add_parser(
        "check",
        help=(
            "aggregate quality gate: ruff, ty, frob cycle/dup/arch/bind/exports; "
            "errors first, easy to hand to subagents"
        ),
    )
    check_p.add_argument("check_path", metavar="path", nargs="?", default=".")
    check_p.add_argument(
        "--type",
        dest="check_type",
        choices=["python", "cpp", "rust", "typescript"],
        help="project type (default: auto-detect)",
    )
    check_p.add_argument(
        "--valgrind",
        dest="check_valgrind",
        action="store_true",
        help="run valgrind memcheck on test binary",
    )
    check_p.add_argument("--skip-tests", dest="check_skip_tests", action="store_true")
    _add_check_skip_args(check_p)
    check_p.add_argument("--json", dest="check_json", action="store_true")
    check_p.add_argument("--ticket", dest="check_ticket", metavar="ID")
    check_p.add_argument("--base", dest="check_base", metavar="REF")
    check_p.add_argument(
        "--only",
        dest="check_only",
        metavar="STAGE",
        action="append",
        default=[],
        help="run only these stages (repeatable); includes 'gates'",
    )
    check_p.add_argument(
        "--stamp-coverage",
        dest="check_stamp_coverage",
        action="store_true",
        help="record coverage.xml as the current coverage stamp and exit",
    )


# frob:ticket T-0030
def _add_gitlog_parser(sub) -> None:
    """Register the `frob gitlog` subcommand and its arguments."""
    # -- gitlog ---------------------------------------------------------------
    gitlog_p = sub.add_parser(
        "gitlog",
        help="summarize git history by type/granularity (conventional commits)",
    )
    gitlog_p.add_argument(
        "gitlog_path",
        metavar="path",
        nargs="?",
        help="git repo root (default: current directory)",
    )
    gitlog_p.add_argument(
        "--level",
        dest="gitlog_granularity",
        choices=["major", "user", "full", "changelog"],
        default="user",
        help="major=breaking only | user=feat+fix | full=all | changelog=release notes",
    )
    gitlog_p.add_argument(
        "--since",
        dest="gitlog_since",
        metavar="TAG_OR_DATE",
        help="start from tag (e.g. v1.0.0) or date (e.g. 2024-01-01)",
    )
    gitlog_p.add_argument("--until", dest="gitlog_until", metavar="TAG_OR_DATE")
    gitlog_p.add_argument(
        "--limit",
        "-n",
        dest="gitlog_limit",
        type=int,
        metavar="N",
        help="max number of commits to fetch",
    )
    gitlog_p.add_argument(
        "--all",
        dest="gitlog_all",
        action="store_true",
        help="include non-conventional commits",
    )
    gitlog_p.add_argument("--json", dest="gitlog_json", action="store_true")


# frob:ticket T-0030
def _add_graph_parser(sub) -> None:
    """Register the `frob graph` subcommand and its arguments."""
    # -- graph -----------------------------------------------------------------
    graph_p = sub.add_parser(
        "graph", help="obligation graph: build cache, query symbols, explain drift"
    )
    graph_sub = graph_p.add_subparsers(dest="graph_command")
    graph_build_p = graph_sub.add_parser("build", help="(re)build the graph cache")
    graph_build_p.add_argument("graph_path", metavar="path", nargs="?", default=".")
    graph_query_p = graph_sub.add_parser(
        "query", help="resolve a symbol ref and show its edges"
    )
    graph_query_p.add_argument("graph_ref", metavar="ref")
    graph_query_p.add_argument("graph_path", metavar="path", nargs="?", default=".")
    graph_query_p.add_argument("--json", dest="graph_json", action="store_true")
    graph_why_p = graph_sub.add_parser(
        "why", help="explain drift/ack status and remedy for a ref"
    )
    graph_why_p.add_argument("graph_ref", metavar="ref")
    graph_why_p.add_argument("graph_path", metavar="path", nargs="?", default=".")
    graph_why_p.add_argument("--json", dest="graph_json", action="store_true")


# frob:ticket T-0030
def _add_ack_parser(sub) -> None:
    """Register the `frob ack` subcommand and its arguments."""
    # -- ack ---------------------------------------------------------------
    ack_p = sub.add_parser(
        "ack", help="acknowledge current digests for one or more symbol refs"
    )
    ack_p.add_argument("ack_refs", metavar="ref", nargs="+")
    ack_p.add_argument(
        "--facet", dest="ack_facet", choices=["sig", "body", "doc"], default="sig"
    )
    ack_p.add_argument("--path", dest="ack_path", metavar="DIR", default=".")


# frob:ticket T-0030
# frob:ticket T-0030
def _add_ticket_new_parser(ticket_sub) -> None:
    """Register `frob ticket new` and its (many) creation flags."""
    ticket_new_p = ticket_sub.add_parser("new", help="create a new ticket")
    ticket_new_p.add_argument("--title", dest="ticket_title", required=True)
    ticket_new_p.add_argument(
        "--kind",
        dest="ticket_kind",
        required=True,
        choices=["feature", "bug", "security", "ux", "docs", "invariant", "incident"],
    )
    ticket_new_p.add_argument(
        "--acceptance",
        dest="ticket_acceptance",
        action="append",
        default=[],
        metavar="CRITERION",
        help="given/when/then acceptance criterion (repeatable)",
    )
    ticket_new_p.add_argument(
        "--threat",
        dest="ticket_threat",
        choices=[
            "spoofing",
            "tampering",
            "repudiation",
            "info-disclosure",
            "denial-of-service",
            "elevation-of-privilege",
        ],
        help="STRIDE category for a kind=security ticket",
    )
    ticket_new_p.add_argument(
        "--origin",
        dest="ticket_origin",
        choices=["human", "agent", "auditor"],
        help="who filed this ticket (default: human)",
    )
    ticket_new_p.add_argument(
        "--scope", dest="ticket_scope", action="append", default=[]
    )
    ticket_new_p.add_argument(
        "--blocked-by", dest="ticket_blocked_by", action="append", default=[]
    )
    ticket_new_p.add_argument("--parent", dest="ticket_parent")
    ticket_new_p.add_argument("--body", dest="ticket_body", default="")
    ticket_new_p.add_argument("--json", dest="ticket_json", action="store_true")
    ticket_new_p.add_argument("--path", dest="ticket_path", metavar="DIR", default=".")


# frob:ticket T-0030
def _add_ticket_query_parsers(ticket_sub) -> list:
    """Register the read-only `list`/`show`/`doable` ticket subcommands."""
    ticket_list_p = ticket_sub.add_parser("list", help="list tickets")
    ticket_list_p.add_argument("--state", dest="ticket_state")
    ticket_list_p.add_argument("--json", dest="ticket_json", action="store_true")

    ticket_show_p = ticket_sub.add_parser("show", help="show one ticket")
    ticket_show_p.add_argument("ticket_id", metavar="id")
    ticket_show_p.add_argument("--json", dest="ticket_json", action="store_true")

    ticket_doable_p = ticket_sub.add_parser(
        "doable", help="list doable tickets (queued/planned, no open blockers)"
    )
    ticket_doable_p.add_argument("--json", dest="ticket_json", action="store_true")
    return [ticket_list_p, ticket_show_p, ticket_doable_p]


# frob:ticket T-0030
def _add_ticket_lifecycle_parsers(ticket_sub) -> list:
    """Register the state-transition ticket subcommands (plan/start/close/...)."""
    ticket_plan_p = ticket_sub.add_parser("plan", help="transition queued -> planned")
    ticket_plan_p.add_argument("ticket_id", metavar="id")

    ticket_start_p = ticket_sub.add_parser(
        "start",
        help="transition to in-progress (auto-plans a queued ticket) and run "
        "the pre-work sweep",
    )
    ticket_start_p.add_argument("ticket_id", metavar="id")

    ticket_sweep_p = ticket_sub.add_parser(
        "sweep", help="re-record the pre-work sweep (after widening scope)"
    )
    ticket_sweep_p.add_argument("ticket_id", metavar="id")

    ticket_migrate_p = ticket_sub.add_parser(
        "migrate", help="collapse legacy tickets/*.md into a single tickets.md ledger"
    )
    ticket_renumber_p = ticket_sub.add_parser(
        "renumber", help="reassign ids to a contiguous T-0001.. sequence"
    )

    ticket_attach_p = ticket_sub.add_parser(
        "attach", help="attach a file or clipboard image to a ticket"
    )
    ticket_attach_p.add_argument("ticket_id", metavar="id")
    ticket_attach_p.add_argument(
        "ticket_attach_path", metavar="path", nargs="?", default=None
    )
    ticket_attach_p.add_argument("--caption", dest="ticket_caption", default="")

    ticket_block_p = ticket_sub.add_parser("block", help="record a blocker")
    ticket_block_p.add_argument("ticket_id", metavar="id")
    ticket_block_p.add_argument("--by", dest="ticket_by", required=True)

    ticket_close_p = ticket_sub.add_parser("close", help="transition to done")
    ticket_close_p.add_argument("ticket_id", metavar="id")

    ticket_fail_p = ticket_sub.add_parser(
        "fail", help="record a failed attempt in the failure log"
    )
    ticket_fail_p.add_argument("ticket_id", metavar="id")
    ticket_fail_p.add_argument("--summary", dest="ticket_summary", required=True)

    ticket_evidence_p = ticket_sub.add_parser(
        "evidence",
        help="append pytest node ids to a ticket's structured evidence list",
    )
    ticket_evidence_p.add_argument("ticket_id", metavar="id")
    ticket_evidence_p.add_argument("ticket_evidence_ids", metavar="node-id", nargs="+")

    ticket_archive_p = ticket_sub.add_parser(
        "archive", help="move done/dropped tickets into tickets-archive.md"
    )
    return [
        ticket_plan_p,
        ticket_start_p,
        ticket_sweep_p,
        ticket_migrate_p,
        ticket_renumber_p,
        ticket_attach_p,
        ticket_block_p,
        ticket_close_p,
        ticket_fail_p,
        ticket_evidence_p,
        ticket_archive_p,
    ]


# frob:ticket T-0030
def _add_ticket_parser(sub) -> None:
    """Register the `frob ticket` subcommand and its arguments."""
    ticket_p = sub.add_parser("ticket", help="the statically-checkable ticket queue")
    ticket_sub = ticket_p.add_subparsers(dest="ticket_command")
    _add_ticket_new_parser(ticket_sub)
    path_parsers = _add_ticket_query_parsers(ticket_sub)
    path_parsers += _add_ticket_lifecycle_parsers(ticket_sub)
    for _tp in path_parsers:
        _tp.add_argument("--path", dest="ticket_path", metavar="DIR", default=".")


# frob:ticket T-0030
def _add_test_parser(sub) -> None:
    """Register the `frob test` subcommand and its arguments."""
    # -- test ----------------------------------------------------------------
    test_p = sub.add_parser(
        "test", help="select and run tests for the touched set (or --all)"
    )
    test_p.add_argument("test_path", metavar="path", nargs="?", default=".")
    test_p.add_argument("--all", dest="test_all", action="store_true")
    test_p.add_argument(
        "--fuzz",
        dest="test_fuzz",
        action="store_true",
        help="property-test fuzz-obligated pydantic models and stamp (T-0002)",
    )
    test_p.add_argument("--base", dest="test_base", metavar="REF")
    test_p.add_argument(
        "--lang", dest="test_lang", action="append", default=[], metavar="L"
    )
    test_p.add_argument(
        "--fallback",
        dest="test_fallback",
        choices=["package", "suite", "warn"],
    )
    test_p.add_argument("--json", dest="test_json", action="store_true")


# frob:ticket T-0030
def _add_vet_parser(sub) -> None:
    """Register the `frob vet` subcommand and its arguments."""
    # -- vet -----------------------------------------------------------------
    vet_p = sub.add_parser(
        "vet",
        help="dependency-vetting: lockfile allow conformance, quarantine, "
        "typosquat, lifecycle scripts, osv advisories",
    )
    vet_p.add_argument("vet_path", metavar="path", nargs="?", default=".")
    vet_p.add_argument(
        "--hook",
        dest="vet_hook",
        metavar="COMMAND",
        help="check an install-shaped shell command before it runs "
        "(Claude Code PreToolUse hook mode)",
    )
    vet_p.add_argument("--json", dest="vet_json", action="store_true")


# frob:ticket T-0030
def _add_perf_parser(sub) -> None:
    """Register the `frob perf` subcommand and its arguments."""
    # -- perf ------------------------------------------------------------------
    perf_p = sub.add_parser(
        "perf", help="profile a command/test suite and inspect its heat-map"
    )
    perf_sub = perf_p.add_subparsers(dest="perf_command")

    perf_profile_p = perf_sub.add_parser(
        "profile", help="run a command under cProfile, storing an artifact"
    )
    perf_profile_p.add_argument("--path", dest="perf_path", metavar="DIR", default=".")
    perf_profile_p.add_argument(
        "--tests",
        dest="perf_tests",
        action="store_true",
        help="profile the [[test.runner]] python entry instead of an argv",
    )
    perf_profile_p.add_argument(
        "perf_argv",
        metavar="argv",
        nargs=argparse.REMAINDER,
        help="command to run under cProfile, after --",
    )

    perf_heat_p = perf_sub.add_parser(
        "heat", help="render the profiled heat-map, ranked by cumulative time"
    )
    perf_heat_p.add_argument("--path", dest="perf_path", metavar="DIR", default=".")
    perf_heat_p.add_argument("--ref", dest="perf_ref", metavar="SHA")
    perf_heat_p.add_argument("--json", dest="perf_json", action="store_true")
    perf_heat_p.add_argument(
        "--smells",
        dest="perf_smells",
        action="store_true",
        help="rank hot symbols that also carry PERF findings first",
    )
    perf_heat_p.add_argument("--top", dest="perf_top", type=int, metavar="N")
    perf_heat_p.add_argument(
        "--annotate",
        dest="perf_annotate",
        metavar="FILE",
        help="print FILE with per-line hit/time gutters",
    )


# frob:ticket T-0030
def _add_release_parser(sub) -> None:
    """Register the `frob release` subcommand and its arguments."""
    # -- release -------------------------------------------------------------
    release_p = sub.add_parser(
        "release", help="mechanical semver from the public-API graph (REL001)"
    )
    release_sub = release_p.add_subparsers(dest="release_command")
    release_stamp_p = release_sub.add_parser(
        "stamp", help="record the current public API + version to .frob-release.json"
    )
    release_stamp_p.add_argument(
        "--path", dest="release_path", metavar="DIR", default="."
    )
    release_check_p = release_sub.add_parser(
        "check", help="verify the version bump covers the public-API change"
    )
    release_check_p.add_argument(
        "--path", dest="release_path", metavar="DIR", default="."
    )


# frob:ticket T-0030
def _add_mutate_parser(sub) -> None:
    """Register the `frob mutate` subcommand and its arguments."""
    # -- mutate --------------------------------------------------------------
    mutate_p = sub.add_parser(
        "mutate", help="mutation testing: perturb a file, see which mutants survive"
    )
    mutate_p.add_argument("mutate_file", metavar="file")
    mutate_p.add_argument("--path", dest="mutate_path", metavar="DIR", default=".")
    mutate_p.add_argument("--json", dest="mutate_json", action="store_true")
    mutate_p.add_argument(
        "mutate_argv",
        metavar="-- test-cmd",
        nargs=argparse.REMAINDER,
        help="test command to run per mutant (after --); default: uv run pytest -q",
    )


# frob:ticket T-0030
def _add_stats_parser(sub) -> None:
    """Register the `frob stats` subcommand and its arguments."""
    # -- stats ---------------------------------------------------------------
    stats_p = sub.add_parser(
        "stats", help="delivery measurement: queue health + commit cadence"
    )
    stats_p.add_argument("--path", dest="stats_path", metavar="DIR", default=".")
    stats_p.add_argument(
        "--days", dest="stats_days", type=int, metavar="N", help="commit window (30)"
    )
    stats_p.add_argument("--json", dest="stats_json", action="store_true")


# frob:ticket T-0030
def _add_serve_parser(sub) -> None:
    """Register the `frob serve` subcommand and its arguments."""
    # -- serve ---------------------------------------------------------------
    serve_p = sub.add_parser(
        "serve",
        help="MCP stdio adapter exposing frob's enforcement queries as tools",
    )
    serve_p.add_argument("serve_path", metavar="path", nargs="?", default=".")


def _build_parser() -> argparse.ArgumentParser:
    # frob:ticket T-0021
    p = argparse.ArgumentParser(
        prog="frob",
        description="Developer workflow tools -- optimized for agentic use",
    )
    sub = p.add_subparsers(dest="subcommand")

    _add_scaffold_parser(sub)
    _add_cycle_parser(sub)
    _add_outline_parser(sub)
    _add_map_parser(sub)
    _add_xref_parser(sub)
    _add_parse_parser(sub)
    _add_dup_parser(sub)
    _add_arch_parser(sub)
    _add_docs_parser(sub)
    _add_exports_parser(sub)
    _add_bind_parser(sub)
    _add_check_parser(sub)
    _add_gitlog_parser(sub)
    _add_graph_parser(sub)
    _add_ack_parser(sub)
    _add_ticket_parser(sub)
    _add_test_parser(sub)
    _add_vet_parser(sub)
    _add_perf_parser(sub)
    _add_release_parser(sub)
    _add_mutate_parser(sub)
    _add_stats_parser(sub)
    _add_serve_parser(sub)
    return p


# frob:doc docs/modules/app.md#entry-point
def main() -> None:
    import sys as _sys

    if len(_sys.argv) > 1 and _sys.argv[1] == "bind":
        from frob.app.bind_runner import run as _bind_run

        _bind_run(_sys.argv[2:])
    else:
        parser = _build_parser()
        args = parser.parse_args()
        cfg = AppConfig.from_external(args, Path("pyproject.toml"))
        App(cfg)()


if __name__ == "__main__":
    main()
