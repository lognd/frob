from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.scaffold.project import list_project_types, render_project
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    cmd = cfg.scaffold_command or cfg.init_command
    if cmd == "list" or cmd is None:
        for t in list_project_types():
            _log.info(t)
        return

    proj_type = cfg.scaffold_type or cfg.init_type
    proj_name = cfg.scaffold_name or cfg.init_name

    if proj_type is None or proj_name is None:
        _log.error("frob scaffold new requires <type> and <name>")
        sys.exit(1)

    out_dir = cfg.scaffold_output or cfg.init_output or Path(".")
    force = cfg.scaffold_force or cfg.init_force
    result = render_project(proj_type, proj_name, out_dir, force=force)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    for p in result.danger_ok:
        _log.info("created %s", p)
