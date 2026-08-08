from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger, quiet_stdout_logs
from frob.map import map_project
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-1479
# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_map_json_daemon_matches_in_process kind="unit"  # noqa: E501
def _try_map_via_daemon(root: Path, cfg: AppConfig) -> bool:
    """T-1479: for a plain `frob map --json` against the daemon's own
    served root (`cfg.map_path` unset or exactly `.`/root -- unlike
    `frob_exports`'s subdirectory-echo convention, this RPC only ever
    answers for `root` itself, so a `frob map <subdir>` call always falls
    through to the in-process path below rather than proxying a target
    the daemon's own lookup by `root` cannot safely disambiguate from),
    try the daemon's RPC (`frob_map`) via `frob.app._daemon_proxy.query`
    before computing it in-process. Returns `True` on a daemon hit
    (already rendered); `False` falls through unchanged, same contract
    every other `_try_*_via_daemon` helper uses. The RPC returns
    `MapResult.model_dump(mode='json')`, field-for-field identical to
    this CLI's own `--json` output (both sides dump the identical
    pydantic model, matching T-1127's `frob_stats`/`frob_exports`
    precedent)."""
    if not cfg.map_json:
        return False
    if cfg.map_path is not None and cfg.map_path != Path("."):
        return False
    from frob.app._daemon_proxy import query

    proxied = query(root, "frob_map", {"depth": cfg.map_depth})
    if proxied.is_err:
        return False
    import json

    _log.info(json.dumps(proxied.danger_ok, indent=2))
    return True


# frob:ticket T-0448
# frob:ticket T-1238
# frob:ticket T-1479
# frob:doc docs/modules/app.md#runners
# frob:doc docs/modules/render.md#exemplar-frob-map
def run(cfg: AppConfig) -> None:
    """Render the `frob map` project structure summary; T-0448: migrated
    to `frob.render.Renderer` as the second FOUNDATION exemplar -- `--json`
    stays a bare structured print, unchanged. T-1238: un-deprecated --
    regrouped under `frob explore map` (`explore_runner.run`), this
    top-level form stays as a permanent alias, not a sunsetting shim.
    T-1479: `--json` against the daemon's own root tries the daemon proxy
    first (`_try_map_via_daemon`)."""
    root = cfg.map_path or Path(".")
    if _try_map_via_daemon(root, cfg):
        return
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
