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
from frob.logging.quiet import quiet_query_stdout
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0563
# frob:ticket T-0803
# frob:ticket T-0815
# frob:ticket T-0588
# frob:doc docs/modules/app.md#runners
# frob:tests tests/unit/test_app_runners.py::TestGitlogRunner.test_json_mode_prints_json
def run(cfg: AppConfig) -> None:
    """`frob gitlog`: report git history grouped by conventional-commit type.

    T-0803: `git_log` now spawns through `guarded_subprocess_run`, which
    logs a DEBUG "spawning" line -- and this repo's stdout log handler is
    DEBUG-level by default (`src/frob/logging/config.toml`), so an
    unguarded call here would leak that line into `--json` output.

    T-2582: quieted in BOTH modes now (`FROB_VERBOSE=1` opts back into
    the diagnostic spawn line) -- human mode used to keep it always
    visible, which drowned the answer in the same way `--json` was
    already protected from."""
    root = cfg.gitlog_path or Path(".")
    with quiet_query_stdout():
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
