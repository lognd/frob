"""CLI wiring for `frob serve` (docs/serve.md): the stdio MCP adapter."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/serve.md#mcp-sdk
def run(cfg: AppConfig) -> None:
    """Start the stdio MCP server rooted at `cfg.serve_path`, exit 1 if unavailable."""
    from frob.serve.server import McpUnavailable, run_stdio

    root = (cfg.serve_path or Path(".")).resolve()
    try:
        run_stdio(root)
    except McpUnavailable as exc:
        _log.error("frob serve: %s", exc)
        sys.exit(1)
