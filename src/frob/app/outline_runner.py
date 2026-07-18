from __future__ import annotations

import contextlib
import sys

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.outline import outline_file

_log = get_logger(__name__)


def _fall_back_to_map(cfg: AppConfig, target) -> None:  # noqa: ANN001
    """`frob outline <dir>`: delegate to `frob map` for a directory target."""
    from frob.app.config import AppConfig as _Cfg
    from frob.app.map_runner import run as map_run

    map_cfg = _Cfg(
        subcommand=cfg.subcommand,
        map_path=target,
        map_json=cfg.outline_json,
        map_all=cfg.outline_all,
    )
    map_run(map_cfg)


# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    if cfg.outline_file is None:
        _log.error("frob outline requires <file>")
        sys.exit(1)

    target = cfg.outline_file
    if target.is_dir():
        _fall_back_to_map(cfg, target)
        return

    ctx = quiet_stdout_logs() if cfg.outline_json else contextlib.nullcontext()
    with ctx:
        result = outline_file(target)
    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    ol = result.danger_ok
    if cfg.outline_json:
        _log.info(ol.as_json())
    else:
        _log.info(ol.as_text(include_private=cfg.outline_all))
