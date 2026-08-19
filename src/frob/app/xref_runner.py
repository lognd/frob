from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.logging.quiet import quiet_query_stdout
from frob.xref import xref

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-0588
# frob:ticket T-1238
# frob:tests tests/unit/test_app_runners.py::TestXrefRunner.test_found_symbol_json_mode
def run(cfg: AppConfig) -> None:
    """`frob xref`: find where a symbol is defined and every file that uses
    it. T-1238: un-deprecated -- regrouped under `frob explore xref`
    (`explore_runner.run`), this top-level form stays as a permanent alias.
    `frob.exports.exports_consumers` remains the narrower "just import
    consumers" answer to the same underlying question (T-0858)."""
    if cfg.xref_symbol is None:
        _log.error("frob xref requires <symbol>")
        sys.exit(1)

    root = cfg.xref_path or Path(".")
    # T-2582: quiet stdout-bound DEBUG/INFO for BOTH modes -- previously
    # only --json was protected, drowning the human-mode answer in
    # thousands of parse-diagnostic lines. FROB_VERBOSE=1 restores them.
    with quiet_query_stdout():
        result = xref(cfg.xref_symbol, root, lang=cfg.xref_lang)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    xr = result.danger_ok
    if cfg.xref_json:
        _log.info(xr.as_json())
    else:
        _log.info(xr.as_text(cross_file=cfg.xref_cross_file))
