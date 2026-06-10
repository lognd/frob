from __future__ import annotations

import argparse
from pathlib import Path

from frob.app import App, AppConfig


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="frob", description="Developer workflow tools")
    sub = p.add_subparsers(dest="subcommand")

    # -- init ----------------------------------------------------------------
    init_p = sub.add_parser("init", help="scaffold a new project from a template")
    init_sub = init_p.add_subparsers(dest="init_command")

    init_sub.add_parser("list", help="list registered project types")

    new_p = init_sub.add_parser("new", help="create a new project")
    new_p.add_argument("init_type", metavar="type", help="project type (e.g. python-tool)")
    new_p.add_argument("init_name", metavar="name", help="project name")
    new_p.add_argument("--output", dest="init_output", metavar="DIR", help="output directory")
    new_p.add_argument("--force", dest="init_force", action="store_true",
                       help="overwrite existing files")

    # -- cycle ---------------------------------------------------------------
    cycle_p = sub.add_parser("cycle", help="detect dependency cycles")
    cycle_p.add_argument("cycle_path", metavar="path", help="file or directory to scan")
    cycle_p.add_argument("--lang", dest="cycle_lang", choices=["python", "cpp", "c"],
                         help="restrict to a single language")
    cycle_p.add_argument("--suggest", dest="cycle_suggest", action="store_true",
                         help="print refactoring suggestions for each cycle")

    # -- stub ----------------------------------------------------------------
    stub_p = sub.add_parser("stub", help="emit a stubbed source file")
    stub_p.add_argument("stub_file", metavar="file", help="source file to stub")
    stub_p.add_argument("stub_target", metavar="target",
                        help="function or ClassName.method to keep intact")
    stub_p.add_argument("--output", dest="stub_output", metavar="FILE",
                        help="write output to FILE instead of stdout")

    return p


if __name__ == "__main__":
    parser = _build_parser()
    args = parser.parse_args()
    cfg = AppConfig.from_external(args, Path("pyproject.toml"))
    App(cfg)()
