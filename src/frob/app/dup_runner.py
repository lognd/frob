from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.dup import find_duplicates
from frob.logging import get_logger

_log = get_logger(__name__)

# AppConfig fields used by this runner (add to AppConfig when wiring CLI):
#   dup_path: Path | None      -- directory to scan (required)
#   dup_min_lines: int         -- minimum function body size (default 6)
#   dup_json: bool             -- emit JSON instead of human-readable text


def run(cfg: AppConfig) -> None:
    dup_path: Path | None = getattr(cfg, "dup_path", None)
    if dup_path is None:
        _log.error("frob dup requires <path>")
        sys.exit(1)

    if not dup_path.exists():
        _log.error("path does not exist: %s", dup_path)
        sys.exit(1)

    min_lines: int = getattr(cfg, "dup_min_lines", 6) or 6
    dup_json: bool = getattr(cfg, "dup_json", False)

    result = find_duplicates(dup_path, min_lines=min_lines)

    if dup_json:
        _log.info("%s", result.as_json())
    else:
        _log.info("%s", result.as_text())
