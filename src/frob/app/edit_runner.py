from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.edit import commit, isolate, replace, stage, status
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    if cfg.edit_file is None:
        _log.error("frob edit requires <file>")
        sys.exit(1)

    path = cfg.edit_file

    # --status: no symbol needed
    if cfg.edit_status:
        patches = status(path)
        if not patches:
            print("no staged patches")
            return
        for p in patches:
            print(f"  {p.symbol}")
        return

    # --commit: no symbol needed
    if cfg.edit_commit:
        result = commit(path)
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        cr = result.danger_ok
        print(f"committed {len(cr.applied)} patch(es): {', '.join(cr.applied)}")
        if cr.skipped:
            _log.warning("duplicate symbol(s) resolved (kept newest): %s", ", ".join(cr.skipped))
        return

    # All other modes require a symbol
    if not cfg.edit_symbol:
        _log.error("frob edit requires <symbol> (omit only with --commit or --status)")
        sys.exit(1)

    symbol = cfg.edit_symbol

    # --stage: write patch file, do not touch source
    if cfg.edit_stage:
        new_source = sys.stdin.read()
        result = stage(path, symbol, new_source)
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        print(f"staged {symbol}  ->  {result.danger_ok}")
        return

    # --replace or --immediate: immediate lock+write
    if cfg.edit_replace or cfg.edit_immediate:
        new_source = sys.stdin.read()
        result = replace(path, symbol, new_source)
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        _log.info("replaced %s in %s", symbol, path)
        return

    # Default: isolate (read-only)
    result = isolate(path, symbol)
    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)
    iso = result.danger_ok
    print(f"# {iso.symbol}  [L{iso.start_line}-L{iso.end_line}]\n{iso.source}")
