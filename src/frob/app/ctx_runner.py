from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.ctx import adaptive_context
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.ctx_file is None or cfg.ctx_symbol is None:
        _log.error("frob ctx requires <file> <symbol>")
        sys.exit(1)

    result = adaptive_context(
        cfg.ctx_file,
        cfg.ctx_symbol,
        root=cfg.ctx_root,
        bundle_depth=cfg.ctx_depth,
    )
    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    cr = result.danger_ok
    if cfg.ctx_json:
        _log.info(cr.model_dump_json(indent=2))
    else:
        _log.info(cr.as_text())
