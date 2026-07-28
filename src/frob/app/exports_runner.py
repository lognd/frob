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


# frob:tests tests/test_app_daemon_proxy.py::TestDifferentialParity.test_exports_json_daemon_matches_in_process kind="unit"  # noqa: E501
def _try_exports_via_daemon(root: Path, cfg: AppConfig) -> bool:
    """T-1127: for a plain `frob exports <path> --json` render (no
    `--consumers`, no `--write` -- the RPC's `frob_exports` has no
    parameter for either), try the daemon's RPC via `frob.app.
    _daemon_proxy.query` before computing it in-process. Returns `True`
    on a daemon hit (already rendered); `False` falls through unchanged,
    same contract every other `_try_*_via_daemon` helper uses. The RPC
    returns `ExportsResult.model_dump(mode='json')` verbatim (T-1127),
    field-for-field identical to this CLI's own `--json` output (both
    sides dump the identical pydantic model)."""
    if not cfg.exports_json or cfg.exports_write:
        return False
    from frob.app._daemon_proxy import query

    proxied = query(
        root,
        "frob_exports",
        {
            "include_private": cfg.exports_all,
            "exclude_modules": cfg.exports_exclude or [],
        },
    )
    if proxied.is_err:
        return False
    import json

    _log.info(json.dumps(proxied.danger_ok, indent=2))
    return True


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

    if _try_exports_via_daemon(cfg.exports_path, cfg):
        return

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
