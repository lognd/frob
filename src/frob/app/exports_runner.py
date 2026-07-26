from __future__ import annotations

import contextlib
import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.exports import exports_consumers, exports_package
from frob.logging import get_logger, quiet_stdout_logs

_log = get_logger(__name__)


# frob:ticket T-0876
# frob:tests tests/unit/test_app_runners.py::TestExportsRunner.test_consumers_mode_logs_result  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExportsRunner.test_consumers_mode_json_output  # noqa: E501
# frob:tests tests/unit/test_app_runners.py::TestExportsRunner.test_consumers_mode_err_result_exits_1  # noqa: E501
def _run_consumers(cfg: AppConfig) -> None:
    """`frob exports --consumers SYMBOL <path>`: log the CLI-level rendering
    of `frob.exports.exports_consumers` (T-0858's library surface), the CLI
    entry point T-0876 was filed to wire on."""
    assert cfg.exports_consumers is not None  # guarded by run()'s caller check
    root = cfg.exports_path or Path(".")
    ctx = quiet_stdout_logs() if cfg.exports_json else contextlib.nullcontext()
    with ctx:
        result = exports_consumers(cfg.exports_consumers, root, lang=cfg.exports_lang)
    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    cr = result.danger_ok
    if cfg.exports_json:
        _log.info(cr.as_json())
    else:
        _log.info(cr.as_text())


# frob:doc docs/modules/app.md#runners
# frob:ticket T-0588
# frob:tests tests/unit/test_app_runners.py::TestExportsRunner.test_json_mode_logs_result  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob exports` entry point: default mode generates a package's
    `__init__.py` listing; `--consumers SYMBOL` instead answers "who imports
    this symbol" via `frob.exports.exports_consumers` (T-0876)."""
    if cfg.exports_consumers is not None:
        _run_consumers(cfg)
        return

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
