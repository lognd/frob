from __future__ import annotations

import contextlib
import sys

from frob.app.config import AppConfig
from frob.exports import exports_package
from frob.logging import get_logger, quiet_stdout_logs

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    if cfg.exports_path is None:
        _log.error("frob exports requires <path>")
        sys.exit(1)

    ctx = quiet_stdout_logs() if cfg.exports_json else contextlib.nullcontext()
    with ctx:
        result = exports_package(
            cfg.exports_path,
            include_private=cfg.exports_all,
            exclude_modules=cfg.exports_exclude or [],
        )
    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    er = result.danger_ok

    if cfg.exports_write:
        init_path = cfg.exports_path / "__init__.py"
        init_path.write_text(er.as_text() + "\n")
        _log.info("wrote %s", init_path)
        return

    if cfg.exports_json:
        _log.info(er.as_json())
    else:
        _log.info(er.as_text())
