from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.tokens import count_paths

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    paths = cfg.tokens_paths or [Path(".")]
    result = count_paths(paths, detail=cfg.tokens_detail)
    if cfg.tokens_json:
        _log.info(result.as_json())
    else:
        _log.info(
            result.as_text(
                detail=cfg.tokens_detail,
                sort=cfg.tokens_sort,
                by_dir=cfg.tokens_by_dir,
            )
        )
