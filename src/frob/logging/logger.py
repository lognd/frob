from __future__ import annotations

import logging
import logging.config
import tomllib
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.toml"
_initialized = False


def _init() -> None:
    global _initialized
    if _initialized:
        return
    with _CONFIG_PATH.open("rb") as f:
        cfg = tomllib.load(f)
    logging.config.dictConfig(cfg)
    _initialized = True


def get_logger(name: str) -> logging.Logger:
    _init()
    return logging.getLogger(name)
