from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig
from frob.gitlog import git_log


# frob:doc docs/app.md#runners
def run(cfg: AppConfig) -> None:
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
        print(result.as_json())
    else:
        print(result.as_text())
