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
# frob:doc docs/modules/app.md#runners
# frob:doc docs/modules/render.md#exemplar-frob-map
# frob:deprecated 2026-07-23 sunset="2026-10-01" ticket="T-0802" reason="zero organic use; navigation owned by Serena/native tools"  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Render the `frob map` project structure summary; T-0448: migrated
    to `frob.render.Renderer` as the second FOUNDATION exemplar -- `--json`
    stays a bare structured print, unchanged. T-0580: DEPRECATED, sunset
    2026-10-01 -- navigation is owned by Serena/native tools in agentic
    use; zero organic invocation observed."""
    _log.warning(
        "frob map is deprecated, sunset 2026-10-01, use Serena/native "
        "navigation; see T-0580"
    )
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
