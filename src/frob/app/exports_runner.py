from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.exports import exports_package
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.exports_path is None:
        _log.error("frob exports requires <path>")
        sys.exit(1)

    result = exports_package(
        cfg.exports_path,
        include_private=cfg.exports_all,
        exclude_modules=cfg.exports_exclude or [],
    )
    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    er = result.danger_ok
    if cfg.exports_json:
        _log.info(er.as_json())
    else:
        _log.info(er.as_text())
