# frob:waive TEST005 reason="module line coverage 0.0%, debt T-0160"
from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.xref import xref

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:waive TEST005 reason="run 0.0% branch cover, debt T-0160"
def run(cfg: AppConfig) -> None:
    if cfg.xref_symbol is None:
        _log.error("frob xref requires <symbol>")
        sys.exit(1)

    root = cfg.xref_path or Path(".")
    ctx = quiet_stdout_logs() if cfg.xref_json else contextlib.nullcontext()
    with ctx:
        result = xref(cfg.xref_symbol, root, lang=cfg.xref_lang)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    xr = result.danger_ok
    if cfg.xref_json:
        _log.info(xr.as_json())
    else:
        _log.info(xr.as_text(cross_file=cfg.xref_cross_file))
