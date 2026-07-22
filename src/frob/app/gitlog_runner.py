"""CLI wiring for `frob gitlog` -- conventional-commit-aware git history
summary. T-0563: routed through `frob.render`/`_log.info` instead of a bare
`print`, matching every other runner (RENDER001 forbids bare stdout writes
outside `frob.render`, including the `--json` escape hatch)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.gitlog import git_log
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0563
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """`frob gitlog`: report git history grouped by conventional-commit type."""
    root = cfg.gitlog_path or Path(".")
    result = git_log(
        root,
        granularity=cfg.gitlog_granularity,  # type: ignore[arg-type]
        since=cfg.gitlog_since,
        until=cfg.gitlog_until,
        limit=cfg.gitlog_limit,
        include_non_conventional=cfg.gitlog_all,
    )
    if cfg.gitlog_json:
        _log.info(result.as_json())
    else:
        r = Renderer.for_stream(sys.stdout)
        r.line(result.as_text())
