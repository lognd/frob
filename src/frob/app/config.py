from __future__ import annotations

import argparse
import enum
from pathlib import Path

from frob._compat import Self, toml
from pydantic import BaseModel


class Subcommand(str, enum.Enum):
    init = "init"
    cycle = "cycle"
    stub = "stub"
    outline = "outline"
    map = "map"
    xref = "xref"
    tokens = "tokens"
    bundle = "bundle"
    parse = "parse"


class AppConfig(BaseModel):
    subcommand: Subcommand | None = None

    # init
    init_command: str | None = None  # "list" or "new"
    init_type: str | None = None
    init_name: str | None = None
    init_output: Path | None = None
    init_force: bool = False

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

    # map
    map_path: Path | None = None
    map_json: bool = False
    map_depth: int | None = None

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
            "init_command", "init_type", "init_name",
            "cycle_lang",
            "stub_target",
            "xref_symbol", "xref_lang",
            "bundle_target", "bundle_format",
            "parse_tool",
        ):
            val = getattr(args, field, None)
            if val is not None:
                d[field] = val

        for path_field in (
            "init_output", "cycle_path",
            "stub_file", "stub_output",
            "outline_file",
            "map_path",
            "xref_path",
            "bundle_file",
            "parse_input",
        ):
            val = getattr(args, path_field, None)
            if val is not None:
                d[path_field] = Path(val)

        # Multi-path field
        token_paths = getattr(args, "tokens_paths", None)
        if token_paths:
            d["tokens_paths"] = [Path(p) for p in token_paths]

        # Int fields
        for int_field in ("map_depth", "bundle_depth"):
            val = getattr(args, int_field, None)
            if val is not None:
                d[int_field] = val

        # Int fields
        parse_ec = getattr(args, "parse_exit_code", None)
        if parse_ec is not None:
            d["parse_exit_code"] = int(parse_ec)

        # Bool flags: only override when explicitly True
        for flag in (
            "init_force", "cycle_suggest",
            "outline_json", "map_json",
            "xref_json", "tokens_detail", "tokens_json",
            "parse_json", "parse_verbose", "parse_passthrough",
        ):
            if getattr(args, flag, False):
                d[flag] = True

        return cls(**d)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> Self:
        return cls.from_external(args, Path("pyproject.toml"))
