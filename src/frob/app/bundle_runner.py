from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.bundle import build_bundle
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.bundle_file is None or cfg.bundle_target is None:
        _log.error("frob bundle requires <file> and <target>")
        sys.exit(1)

    result = build_bundle(cfg.bundle_file, cfg.bundle_target, depth=cfg.bundle_depth)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    bundle = result.danger_ok
    fmt = cfg.bundle_format
    if fmt == "json":
        _log.info(bundle.as_json())
    else:
        _log.info(bundle.as_markdown())
