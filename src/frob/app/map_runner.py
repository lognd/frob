from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.map import map_project
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0448
# frob:ticket T-1238
# frob:doc docs/modules/app.md#runners
# frob:doc docs/modules/render.md#exemplar-frob-map
def run(cfg: AppConfig) -> None:
    """Render the `frob map` project structure summary; T-0448: migrated
    to `frob.render.Renderer` as the second FOUNDATION exemplar -- `--json`
    stays a bare structured print, unchanged. T-1238: un-deprecated --
    regrouped under `frob explore map` (`explore_runner.run`), this
    top-level form stays as a permanent alias, not a sunsetting shim."""
    root = cfg.map_path or Path(".")
    ctx = quiet_stdout_logs() if cfg.map_json else contextlib.nullcontext()
    with ctx:
        result = map_project(root, depth=cfg.map_depth)
    if cfg.map_json:
        _log.info(result.as_json())
    else:
        r = Renderer.for_stream(
            sys.stdout, color_flag=cfg.color, no_color_flag=cfg.no_color
        )
        text = result.as_text(include_private=cfg.map_all)
        first_line, _, rest = text.partition("\n")
        r.write.heading(first_line)
        if rest:
            r.line(rest)
