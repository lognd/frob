from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.xref import xref

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:deprecated 2026-07-23 sunset="2026-10-01" ticket="T-0580" reason="zero organic use across 1035 CLI events; navigation owned by Serena/native tools"
def run(cfg: AppConfig) -> None:
    """T-0580: DEPRECATED, sunset 2026-10-01 -- navigation is owned by
    Serena/native tools in agentic use; zero organic invocation observed."""
    _log.warning(
        "frob xref is deprecated, sunset 2026-10-01, use Serena/native "
        "navigation; see T-0580"
    )
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
