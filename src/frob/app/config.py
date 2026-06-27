from __future__ import annotations

import argparse
import enum
from pathlib import Path

from pydantic import BaseModel

from frob._compat import Self, toml


class Subcommand(str, enum.Enum):
    init = "init"
    scaffold = "scaffold"
    cycle = "cycle"
    stub = "stub"
    outline = "outline"
    map = "map"
    xref = "xref"
    tokens = "tokens"
    bundle = "bundle"
    parse = "parse"
    dup = "dup"
    arch = "arch"
    inspect = "inspect"
    docs = "docs"
    bind = "bind"
    exports = "exports"
    edit = "edit"


class AppConfig(BaseModel):
    subcommand: Subcommand | None = None

    # init (legacy alias for scaffold)
    init_command: str | None = None
    init_type: str | None = None
    init_name: str | None = None
    init_output: Path | None = None
    init_force: bool = False

    # scaffold
    scaffold_command: str | None = None
    scaffold_type: str | None = None
    scaffold_name: str | None = None
    scaffold_output: Path | None = None
    scaffold_force: bool = False

    # cycle
    cycle_path: Path | None = None
    cycle_lang: str | None = None
    cycle_suggest: bool = False

    # stub
    stub_file: Path | None = None
    stub_target: str | None = None
    stub_output: Path | None = None

    # outline
    outline_file: Path | None = None
    outline_json: bool = False
    outline_all: bool = False

    # map
    map_path: Path | None = None
    map_json: bool = False
    map_depth: int | None = None
    map_all: bool = False

    # xref
    xref_symbol: str | None = None
    xref_path: Path | None = None
    xref_lang: str | None = None
    xref_json: bool = False

    # tokens
    tokens_paths: list[Path] = []
    tokens_detail: bool = False
    tokens_json: bool = False

    # bundle
    bundle_file: Path | None = None
    bundle_target: str | None = None
    bundle_depth: int = 1
    bundle_format: str = "markdown"

    # dup
    dup_path: Path | None = None
    dup_min_lines: int = 6
    dup_json: bool = False

    # arch
    arch_path: Path | None = None
    arch_json: bool = False
    arch_max_function_lines: int = 30
    arch_max_class_methods: int = 12

    # inspect
    inspect_project: Path | None = None
    inspect_pycharm: Path | None = None
    inspect_profile: Path | None = None
    inspect_output_dir: Path | None = None
    inspect_scope: str | None = None
    inspect_json: bool = False

    # docs
    docs_path: Path | None = None
    docs_symbol: str | None = None
    docs_overview: bool = False
    docs_search: str | None = None
    docs_json: bool = False

    # exports
    exports_path: Path | None = None
    exports_all: bool = False
    exports_exclude: list[str] = []
    exports_json: bool = False

    # edit
    edit_file: Path | None = None
    edit_symbol: str | None = None
    edit_replace: bool = False

    # parse
    parse_tool: str | None = None
    parse_input: Path | None = None
    parse_exit_code: int = 0
    parse_json: bool = False
    parse_verbose: bool = False
    parse_passthrough: bool = False

    @classmethod
    def from_external(cls, args: argparse.Namespace, file: Path) -> Self:
        file_cfg: dict = {}
        if file.exists():
            with file.open("rb") as f:
                data = toml.load(f)
            file_cfg = data.get("tool", {}).get("frob", {})

        d: dict = {**file_cfg}

        sub = getattr(args, "subcommand", None)
        if sub is not None:
            d["subcommand"] = Subcommand(sub)

        for field in (
            "init_command",
            "init_type",
            "init_name",
            "scaffold_command",
            "scaffold_type",
            "scaffold_name",
            "cycle_lang",
            "stub_target",
            "xref_symbol",
            "xref_lang",
            "bundle_target",
            "bundle_format",
            "parse_tool",
            "inspect_scope",
            "docs_symbol",
            "docs_search",
            "edit_symbol",
        ):
            val = getattr(args, field, None)
            if val is not None:
                d[field] = val

        for path_field in (
            "init_output",
            "scaffold_output",
            "cycle_path",
            "stub_file",
            "stub_output",
            "outline_file",
            "map_path",
            "xref_path",
            "bundle_file",
            "parse_input",
            "dup_path",
            "arch_path",
            "docs_path",
            "inspect_project",
            "inspect_pycharm",
            "inspect_profile",
            "inspect_output_dir",
            "exports_path",
            "edit_file",
        ):
            val = getattr(args, path_field, None)
            if val is not None:
                d[path_field] = Path(val)

        # Multi-path field
        token_paths = getattr(args, "tokens_paths", None)
        if token_paths:
            d["tokens_paths"] = [Path(p) for p in token_paths]

        # Int fields
        for int_field in (
            "map_depth",
            "bundle_depth",
            "dup_min_lines",
            "arch_max_function_lines",
            "arch_max_class_methods",
        ):
            val = getattr(args, int_field, None)
            if val is not None:
                d[int_field] = val

        # Int fields
        parse_ec = getattr(args, "parse_exit_code", None)
        if parse_ec is not None:
            d["parse_exit_code"] = int(parse_ec)

        # Multi-value list fields
        exports_exclude = getattr(args, "exports_exclude", None)
        if exports_exclude:
            d["exports_exclude"] = exports_exclude

        # Bool flags: only override when explicitly True
        for flag in (
            "init_force",
            "scaffold_force",
            "cycle_suggest",
            "outline_json",
            "outline_all",
            "map_json",
            "map_all",
            "xref_json",
            "tokens_detail",
            "tokens_json",
            "parse_json",
            "parse_verbose",
            "parse_passthrough",
            "dup_json",
            "arch_json",
            "inspect_json",
            "docs_json",
            "docs_overview",
            "exports_all",
            "exports_json",
            "edit_replace",
        ):
            if getattr(args, flag, False):
                d[flag] = True

        return cls(**d)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> Self:
        return cls.from_external(args, Path("pyproject.toml"))
