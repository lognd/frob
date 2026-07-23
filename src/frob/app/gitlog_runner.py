"""CLI wiring for `frob gitlog` -- conventional-commit-aware git history
summary. T-0563: routed through `frob.render`/`_log.info` instead of a bare
`print`, matching every other runner (RENDER001 forbids bare stdout writes
outside `frob.render`, including the `--json` escape hatch)."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.gitlog import git_log
from frob.logging import get_logger, quiet_stdout_logs
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0563
# frob:ticket T-0803
# frob:ticket T-0815
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """`frob gitlog`: report git history grouped by conventional-commit type.

    T-0803: `git_log` now spawns through `guarded_subprocess_run`, which
    logs a DEBUG "spawning" line -- and this repo's stdout log handler is
    DEBUG-level by default (`src/frob/logging/config.toml`), so an
    unguarded call here would leak that line into `--json` output.

    T-0815: aligned to the conditional pattern every other `--json` runner
    uses (`frob.app.xref_runner`) -- `quiet_stdout_logs()` only when
    `--json` is requested, so human mode keeps the diagnostic spawn line
    visible instead of always suppressing it."""
    root = cfg.gitlog_path or Path(".")
    ctx = quiet_stdout_logs() if cfg.gitlog_json else contextlib.nullcontext()
    with ctx:
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
