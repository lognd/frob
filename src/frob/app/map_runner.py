# frob:waive TEST005 reason="module line coverage 0.0%, debt T-0160"
from __future__ import annotations

import contextlib
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.map import map_project

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:waive TEST005 reason="run 0.0% branch cover, debt T-0160"
def run(cfg: AppConfig) -> None:
    root = cfg.map_path or Path(".")
    ctx = quiet_stdout_logs() if cfg.map_json else contextlib.nullcontext()
    with ctx:
        result = map_project(root, depth=cfg.map_depth)
    if cfg.map_json:
        _log.info(result.as_json())
    else:
        _log.info(result.as_text(include_private=cfg.map_all))
