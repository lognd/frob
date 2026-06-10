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

    # -- init ----------------------------------------------------------------
    init_p = sub.add_parser("init", help="scaffold a new project from a template")
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
        "stub", help="emit a source file stubbed to a single target"
    )
    stub_p.add_argument("stub_file", metavar="file")
    stub_p.add_argument(
        "stub_target",
        metavar="target",
        help="function or ClassName.method to keep intact",
    )
    stub_p.add_argument("--output", dest="stub_output", metavar="FILE")

    # -- outline -------------------------------------------------------------
    outline_p = sub.add_parser(
        "outline",
        help="show structural skeleton of a file (classes, functions, line numbers)",
    )
    outline_p.add_argument("outline_file", metavar="file")
    outline_p.add_argument("--json", dest="outline_json", action="store_true")

    # -- map -----------------------------------------------------------------
    map_p = sub.add_parser(
        "map",
        help="show whole-project structural map (symbols + line counts)",
    )
    map_p.add_argument("map_path", metavar="path", nargs="?", default=".")
    map_p.add_argument("--json", dest="map_json", action="store_true")
    map_p.add_argument("--depth", dest="map_depth", type=int, metavar="N")

    # -- xref ----------------------------------------------------------------
    xref_p = sub.add_parser(
        "xref",
        help="find where a symbol is defined and every file that uses it",
    )
    xref_p.add_argument("xref_symbol", metavar="symbol")
    xref_p.add_argument("xref_path", metavar="path", nargs="?", default=".")
    xref_p.add_argument("--lang", dest="xref_lang", choices=["python", "cpp", "c"])
    xref_p.add_argument("--json", dest="xref_json", action="store_true")

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
    docs_p.add_argument("docs_path", metavar="path", help="file or directory to inspect")
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

    return p


if __name__ == "__main__":
    import sys as _sys
    if len(_sys.argv) > 1 and _sys.argv[1] == "bind":
        from frob.app.bind_runner import run as _bind_run
        _bind_run(_sys.argv[2:])
    else:
        parser = _build_parser()
        args = parser.parse_args()
        cfg = AppConfig.from_external(args, Path("pyproject.toml"))
        App(cfg)()
