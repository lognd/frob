from __future__ import annotations

import argparse
from pathlib import Path

from frob.app import App, AppConfig


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="frob",
        description="Developer workflow tools -- optimized for agentic use",
    )
    sub = p.add_subparsers(dest="subcommand")

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

    # -- init (alias for scaffold) -------------------------------------------
    init_p = sub.add_parser("init", help="alias for scaffold (deprecated)")
    init_sub = init_p.add_subparsers(dest="init_command")
    init_sub.add_parser("list", help="list registered project types")
    new_p = init_sub.add_parser("new", help="create a new project")
    new_p.add_argument(
        "init_type", metavar="type", help="project type (e.g. python-tool)"
    )
    new_p.add_argument("init_name", metavar="name", help="project name")
    new_p.add_argument("--output", dest="init_output", metavar="DIR")
    new_p.add_argument(
        "--force",
        dest="init_force",
        action="store_true",
        help="overwrite existing files",
    )

    # -- cycle ---------------------------------------------------------------
    cycle_p = sub.add_parser("cycle", help="detect dependency cycles")
    cycle_p.add_argument("cycle_path", metavar="path")
    cycle_p.add_argument("--lang", dest="cycle_lang", choices=["python", "cpp", "c"])
    cycle_p.add_argument("--suggest", dest="cycle_suggest", action="store_true")

    # -- stub ----------------------------------------------------------------
    stub_p = sub.add_parser(
        "stub", help="emit a source file with all functions stubbed except targets"
    )
    stub_p.add_argument("stub_file", metavar="file")
    stub_p.add_argument(
        "stub_targets",
        metavar="target",
        nargs="+",
        help="one or more functions or ClassName.method to keep intact",
    )
    stub_p.add_argument("--output", dest="stub_output", metavar="FILE")

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

    # -- tokens --------------------------------------------------------------
    tokens_p = sub.add_parser(
        "tokens",
        help="estimate token cost of files before reading them",
    )
    tokens_p.add_argument("tokens_paths", metavar="path", nargs="+")
    tokens_p.add_argument(
        "--detail",
        dest="tokens_detail",
        action="store_true",
        help="break down by function/class region",
    )
    tokens_p.add_argument("--json", dest="tokens_json", action="store_true")
    tokens_p.add_argument(
        "--sort",
        dest="tokens_sort",
        action="store_true",
        help="sort files by token count (largest first)",
    )
    tokens_p.add_argument(
        "--by-dir",
        dest="tokens_by_dir",
        action="store_true",
        help="show per-directory subtotals instead of per-file",
    )

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
            "pycharm",
            "cargo",
            "clang-tidy",
            "valgrind",
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

    # -- bundle --------------------------------------------------------------
    bundle_p = sub.add_parser(
        "bundle",
        help="assemble minimal context for a subagent (stubbed file + import sigs)",
    )
    bundle_p.add_argument("bundle_file", metavar="file")
    bundle_p.add_argument("bundle_target", metavar="target")
    bundle_p.add_argument(
        "--depth",
        dest="bundle_depth",
        type=int,
        default=1,
        metavar="N",
        help="how many import levels to inline (default: 1)",
    )
    bundle_p.add_argument(
        "--format",
        dest="bundle_format",
        choices=["markdown", "json"],
        default="markdown",
    )

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

    # -- inspect -------------------------------------------------------------
    inspect_p = sub.add_parser(
        "inspect",
        help="run PyCharm headless inspection and parse results",
    )
    inspect_p.add_argument(
        "inspect_project", metavar="project_dir", help="path to the project to inspect"
    )
    inspect_p.add_argument(
        "--pycharm",
        dest="inspect_pycharm",
        metavar="PATH",
        help="path to PyCharm inspect.bat",
    )
    inspect_p.add_argument(
        "--profile",
        dest="inspect_profile",
        metavar="PATH",
        help="path to inspection profile XML",
    )
    inspect_p.add_argument(
        "--output-dir",
        dest="inspect_output_dir",
        metavar="DIR",
        help="directory for inspection output (default: temp dir)",
    )
    inspect_p.add_argument(
        "--scope",
        dest="inspect_scope",
        metavar="DIR",
        help="subdirectory scope for inspection (e.g. src)",
    )
    inspect_p.add_argument("--json", dest="inspect_json", action="store_true")

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

    # -- edit ----------------------------------------------------------------
    edit_p = sub.add_parser(
        "edit",
        help="isolate or replace a single function/class in a file",
    )
    edit_p.add_argument("edit_file", metavar="file")
    edit_p.add_argument(
        "edit_symbol",
        metavar="symbol",
        nargs="?",
        help="symbol name (omit with --commit/--status)",
    )
    mode = edit_p.add_mutually_exclusive_group()
    mode.add_argument(
        "--replace",
        dest="edit_replace",
        action="store_true",
        help="(legacy) immediate lock+write; equivalent to --immediate",
    )
    mode.add_argument(
        "--stage",
        dest="edit_stage",
        action="store_true",
        help="stage replacement from stdin for later --commit",
    )
    mode.add_argument(
        "--immediate",
        dest="edit_immediate",
        action="store_true",
        help="apply replacement from stdin now under exclusive lock (single-agent)",
    )
    mode.add_argument(
        "--commit",
        dest="edit_commit",
        action="store_true",
        help="apply all staged patches for this file atomically",
    )
    mode.add_argument(
        "--status",
        dest="edit_status",
        action="store_true",
        help="show staged patches for this file",
    )

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
        choices=["python", "cpp", "rust"],
        help="project type (default: auto-detect)",
    )
    check_p.add_argument(
        "--pycharm",
        dest="check_pycharm",
        metavar="PATH",
        help="path to PyCharm inspect.bat/sh (auto-located by default)",
    )
    check_p.add_argument(
        "--valgrind",
        dest="check_valgrind",
        action="store_true",
        help="run valgrind memcheck on test binary",
    )
    check_p.add_argument("--skip-tests", dest="check_skip_tests", action="store_true")
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
    check_p.add_argument("--json", dest="check_json", action="store_true")

    # -- mission -------------------------------------------------------------
    mission_p = sub.add_parser(
        "mission",
        help="create/manage subagent task briefings (.frob/missions/<id>.md)",
    )
    mission_sub = mission_p.add_subparsers(dest="mission_command")

    # mission new
    new_m = mission_sub.add_parser("new", help="create a new mission briefing")
    new_m.add_argument(
        "mission_type", metavar="type", choices=["fix", "test", "implement", "review"]
    )
    new_m.add_argument("--file", dest="mission_file", metavar="FILE")
    new_m.add_argument("--target", dest="mission_target", metavar="SYMBOL")
    new_m.add_argument(
        "--error",
        dest="mission_error",
        metavar="TEXT",
        help="error message to include in the briefing",
    )
    new_m.add_argument(
        "--test",
        dest="mission_test",
        metavar="TEST_NAME",
        help="specific test name to (re-)run",
    )
    new_m.add_argument(
        "--context",
        dest="mission_context",
        metavar="TEXT",
        help="additional freeform context to append",
    )

    # mission done
    done_m = mission_sub.add_parser(
        "done", help="mark mission complete and delete briefing"
    )
    done_m.add_argument("mission_id", metavar="id")

    # mission stuck
    stuck_m = mission_sub.add_parser(
        "stuck", help="mark mission blocked (moves to stuck/)"
    )
    stuck_m.add_argument("mission_id", metavar="id")
    stuck_m.add_argument("mission_reason", metavar="reason")

    # mission list
    mission_sub.add_parser("list", help="list pending missions")

    # -- ctx -----------------------------------------------------------------
    ctx_p = sub.add_parser(
        "ctx",
        help=(
            "adaptive context: chooses stub/bundle/full based on function complexity; "
            "use instead of manually deciding between stub, bundle, xref"
        ),
    )
    ctx_p.add_argument("ctx_file", metavar="file")
    ctx_p.add_argument(
        "ctx_symbol",
        metavar="symbol",
        help="function or class name (ClassName.method for methods)",
    )
    ctx_p.add_argument(
        "--root",
        dest="ctx_root",
        metavar="DIR",
        help="project root for xref search (default: file parent)",
    )
    ctx_p.add_argument(
        "--depth",
        dest="ctx_depth",
        type=int,
        default=1,
        metavar="N",
        help="bundle import depth (default: 1)",
    )
    ctx_p.add_argument("--json", dest="ctx_json", action="store_true")

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

    # -- dispatch -------------------------------------------------------------
    dispatch_p = sub.add_parser(
        "dispatch",
        help="branch-per-agent worktree isolation for thread-safe parallel work",
    )
    dispatch_sub = dispatch_p.add_subparsers(dest="dispatch_command")

    create_d = dispatch_sub.add_parser(
        "create", help="create a worktree branch for an agent"
    )
    create_d.add_argument(
        "dispatch_label",
        metavar="label",
        help="short description (used in branch name)",
    )

    collect_d = dispatch_sub.add_parser(
        "collect", help="rebase+merge completed dispatch branch"
    )
    collect_d.add_argument("dispatch_id", metavar="id")
    collect_d.add_argument(
        "--strategy",
        dest="dispatch_strategy",
        choices=["rebase", "merge"],
        default="rebase",
        help="rebase=linear history (default) or merge=explicit merge commit",
    )

    abort_d = dispatch_sub.add_parser(
        "abort", help="discard a dispatch branch and worktree"
    )
    abort_d.add_argument("dispatch_id", metavar="id")

    dispatch_sub.add_parser("list", help="list active dispatch worktrees")

    # -- todo -----------------------------------------------------------------
    todo_p = sub.add_parser(
        "todo",
        help="persistent TODO tracker for cross-session context (.frob/todo.md)",
    )
    todo_sub = todo_p.add_subparsers(dest="todo_command")

    add_t = todo_sub.add_parser("add", help="add a TODO item")
    add_t.add_argument("todo_text", metavar="text")

    done_t = todo_sub.add_parser("done", help="mark item done")
    done_t.add_argument("todo_id", metavar="id", type=int)

    rm_t = todo_sub.add_parser("remove", help="remove item")
    rm_t.add_argument("todo_id", metavar="id", type=int)

    list_t = todo_sub.add_parser("list", help="list TODO items")
    list_t.add_argument(
        "--all", dest="todo_all", action="store_true", help="include completed items"
    )

    todo_sub.add_parser("clear-done", help="remove all completed items")

    return p


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
