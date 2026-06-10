from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.outline import outline_file

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.outline_file is None:
        _log.error("frob outline requires <file>")
        sys.exit(1)

    result = outline_file(cfg.outline_file)
    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    ol = result.danger_ok
    if cfg.outline_json:
        _log.info(ol.as_json())
    else:
        _log.info(ol.as_text())
