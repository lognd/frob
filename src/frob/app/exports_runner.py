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
# frob:tests tests/unit/test_app_runners.py::TestExportsRunner.test_json_mode_logs_result kind="unit"  # noqa: E501
def _try_exports_via_daemon(pkg_dir: Path, cfg: AppConfig) -> bool:
    """T-1127: for a plain `frob exports <path> --json` render (no
    `--consumers`, no `--write` -- the RPC's `frob_exports` has no
    parameter for either), try the daemon's RPC via `frob.app.
    _daemon_proxy.query` before computing it in-process. Returns `True`
    on a daemon hit (already rendered); `False` falls through unchanged,
    same contract every other `_try_*_via_daemon` helper uses.

    Unlike the other proxied commands (which all answer for the whole
    repo `root`), `frob exports <path>` answers for one SUBDIRECTORY, and
    the daemon a given `root` connects to lives at the REPO root, not
    `pkg_dir` -- `frob.gitio.repo_root(pkg_dir)` finds it, and `pkg_dir`
    itself (verbatim, as typed) is sent as an explicit RPC param so the
    server resolves the identical directory rather than assuming it
    equals its own root. The RPC echoes `str(Path(pkg_dir))` straight back
    as `package_dir` (`ExportsResult.model_dump(mode='json')` otherwise
    verbatim, T-1127) -- byte-for-byte identical to this CLI's own
    `--json` output PROVIDED the daemon's own process cwd agrees with this
    call's cwd on what `pkg_dir`'s relative string resolves to (true for
    a freshly-spawned daemon, since `ensure_daemon`'s spawn inherits this
    process's cwd; a long-lived daemon queried from a DIFFERENT cwd than
    it was spawned from is a known, disclosed edge the fixed-arity
    per-repo RPCs do not share -- see docs/modules/serve.md)."""
    if not cfg.exports_json or cfg.exports_write:
        return False
    from frob.gitio import repo_root

    # T-1006: `repo_root`'s own `gitio` DEBUG logging (every `git`
    # subprocess it spawns) and `query`'s RPC round trip both ran OUTSIDE
    # `run()`'s `quiet_stdout_logs()` context (that context previously wrapped
    # the non-daemon `exports_package` fallback below it) -- a DEBUG log
    # line from `repo_root` landed straight on stdout ahead of the JSON
    # payload this whole call exists to keep machine-parseable, corrupting
    # it for any daemon-hit `--json` run. Wrap this entire helper's body
    # in the same `quiet_stdout_logs()` the fallback path already uses.
    with quiet_stdout_logs():
        root_result = repo_root(pkg_dir)
        if root_result.is_err:
            return False

        from frob.app._daemon_proxy import query

        proxied = query(
            root_result.danger_ok,
            "frob_exports",
            {
                "pkg_dir": str(pkg_dir),
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
