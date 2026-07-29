from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.xref import xref

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:deprecated 2026-07-23 sunset="2026-10-01" ticket="T-1238" reason="sunset rescinded 2026-07-29: regroups under frob explore instead of removal"  # noqa: E501
# frob:ticket T-0588
# frob:tests tests/unit/test_app_runners.py::TestXrefRunner.test_found_symbol_json_mode
def run(cfg: AppConfig) -> None:
    """T-0580: DEPRECATED, sunset 2026-10-01 -- navigation is owned by
    Serena/native tools in agentic use; zero organic invocation observed.
    T-0858 reevaluated the sunset and kept it: the "who imports this
    symbol" question the standalone command answers is recurring and
    gate-driven, but it now lives in `frob.exports.exports_consumers`
    instead of this porcelain."""
    _log.warning(
        "frob xref is deprecated, sunset 2026-10-01, use Serena/native "
        "navigation or frob.exports.exports_consumers for import-consumer "
        "lookups; see T-0580/T-0858"
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
