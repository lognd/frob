from __future__ import annotations

import os
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.docs import extract_docstrings, find_docs_dir, overview, search
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    path = cfg.docs_path
    if path is None:
        _log.error("frob docs requires <path>")
        sys.exit(1)
    if not path.exists():
        _log.error(f"error: {path} does not exist")
        sys.exit(1)

    if cfg.docs_search:
        docs_dir = find_docs_dir(path)
        if not docs_dir:
            _log.error("error: no docs/ directory found")
            sys.exit(1)
        matches = search(cfg.docs_search, docs_dir)
        if cfg.docs_json:
            import json

            _log.info(json.dumps([m.model_dump() for m in matches], indent=2))
        else:
            if not matches:
                _log.info("no matches found")
            for m in matches:
                _log.info(f"{m.file}:{m.line}  [{m.heading}]")
                _log.info(f"  {m.excerpt}")
        return

    if cfg.docs_overview:
        docs_dir = find_docs_dir(path)
        if not docs_dir:
            _log.info("no docs/ directory found")
            return
        entries = overview(path, cfg.docs_symbol)
        if cfg.docs_json:
            import json

            _log.info(json.dumps([e.model_dump() for e in entries], indent=2))
        else:
            for e in entries:
                _log.info(f"## {e.heading}  ({e.file}:{e.line})")
                if e.summary:
                    _log.info(f"   {e.summary}")
        return

    if path.is_dir():
        results = []
        for root, _, files in os.walk(path):
            for f in files:
                if f.endswith(".py"):
                    results.extend(
                        extract_docstrings(Path(root) / f, cfg.docs_symbol)
                    )
    else:
        results = extract_docstrings(path, cfg.docs_symbol)

    if cfg.docs_json:
        import json

        _log.info(json.dumps([d.model_dump() for d in results], indent=2))
    else:
        if not results:
            _log.info("no docstrings found")
            return
        for d in results:
            _log.info(f"[L{d.line}] {d.symbol} ({d.kind})")
            for line in d.text.splitlines():
                _log.info(f"  {line}")
            _log.info("")
