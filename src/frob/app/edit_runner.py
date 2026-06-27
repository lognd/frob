from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.edit import isolate, replace
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.edit_file is None or cfg.edit_symbol is None:
        _log.error("frob edit requires <file> <symbol>")
        sys.exit(1)

    if cfg.edit_replace:
        new_source = sys.stdin.read()
        result = replace(cfg.edit_file, cfg.edit_symbol, new_source)
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        _log.info("replaced %s in %s", cfg.edit_symbol, cfg.edit_file)
    else:
        result = isolate(cfg.edit_file, cfg.edit_symbol)
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        iso = result.danger_ok
        _log.info("# %s  [L%d-L%d]\n%s", iso.symbol, iso.start_line, iso.end_line, iso.source)
