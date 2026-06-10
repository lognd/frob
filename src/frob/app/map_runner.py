from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.map import map_project

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    root = cfg.map_path or Path(".")
    result = map_project(root, depth=cfg.map_depth)
    if cfg.map_json:
        _log.info(result.as_json())
    else:
        _log.info(result.as_text())
