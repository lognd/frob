from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.check import run_check
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    root = cfg.check_path or Path(".")
    result = run_check(
        root,
        skip_ruff=cfg.check_skip_ruff,
        skip_ty=cfg.check_skip_ty,
        skip_arch=cfg.check_skip_arch,
        skip_cycle=cfg.check_skip_cycle,
        skip_dup=cfg.check_skip_dup,
        skip_bind=cfg.check_skip_bind,
        skip_exports=cfg.check_skip_exports,
        pycharm_path=cfg.check_pycharm,
    )
    if cfg.check_json:
        _log.info(result.as_json())
    else:
        _log.info(result.as_text())

    if result.total_errors > 0:
        sys.exit(1)
