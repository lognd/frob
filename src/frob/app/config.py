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

        for field in ("init_command", "init_type", "init_name", "cycle_lang", "stub_target"):
            val = getattr(args, field, None)
            if val is not None:
                d[field] = val

        # Bool flags: only let CLI win when explicitly set to True
        for flag in ("init_force", "cycle_suggest"):
            if getattr(args, flag, False):
                d[flag] = True

        for path_field in ("init_output", "cycle_path", "stub_file", "stub_output"):
            val = getattr(args, path_field, None)
            if val is not None:
                d[path_field] = Path(val)

        return cls(**d)

    @classmethod
    def from_args(cls, args: argparse.Namespace) -> Self:
        return cls.from_external(args, Path("pyproject.toml"))
