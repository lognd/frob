from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.init.project import list_project_types, render_project
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.init_command == "list" or cfg.init_command is None:
        for t in list_project_types():
            _log.info(t)
        return

    if cfg.init_type is None or cfg.init_name is None:
        _log.error("frob init new requires <type> and <name>")
        sys.exit(1)

    out_dir = cfg.init_output or Path(".")
    result = render_project(cfg.init_type, cfg.init_name, out_dir, force=cfg.init_force)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    for p in result.danger_ok:
        _log.info("created %s", p)
