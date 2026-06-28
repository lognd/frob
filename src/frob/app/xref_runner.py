from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.xref import xref

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.xref_symbol is None:
        _log.error("frob xref requires <symbol>")
        sys.exit(1)

    root = cfg.xref_path or Path(".")
    result = xref(cfg.xref_symbol, root, lang=cfg.xref_lang)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    xr = result.danger_ok
    if cfg.xref_json:
        _log.info(xr.as_json())
    else:
        _log.info(xr.as_text(cross_file=cfg.xref_cross_file))
