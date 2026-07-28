from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.scaffold._managed import apply_managed_blocks
from frob.scaffold._pool import lease_worktree, pool_status, warm_pool
from frob.scaffold.project import list_project_types, render_project

_log = get_logger(__name__)


# frob:ticket T-0877
# frob:tests tests/system/test_scaffold_pool_cli.py::TestScaffoldPoolCli.test_warm_lease_status_roundtrip  # noqa: E501
# frob:waive ARCH103 reason="T-0977: thin CLI wrapper dispatching to \
# warm_pool/lease_worktree/pool_status by subcommand and rendering the result \
# text-or-json -- the dispatch+render IS this wrapper's whole documented job (see \
# docstring)"
def _run_pool(cfg: AppConfig) -> None:
    """`frob scaffold pool warm/lease/status` (T-0877): thin CLI wrapper
    over `frob.scaffold._pool`'s `warm_pool`/`lease_worktree`/
    `pool_status`, the same three operations the Makefile's
    `pool-warm`/`pool-lease`/`pool-status` inline-python shims called
    directly -- this is what those targets now delegate to."""
    pool_cmd = cfg.scaffold_pool_command
    repo_root = Path(".")

    if pool_cmd == "warm":
        warmed = warm_pool(repo_root, cfg.scaffold_pool_n)
        if warmed.is_err:
            _log.error("pool-warm failed: %s", warmed.danger_err.value)
            sys.exit(1)
        for entry in warmed.danger_ok:
            _log.info("%d: %s ready=%s", entry.index, entry.path, entry.ready)
        return

    if pool_cmd == "lease":
        leased = lease_worktree(repo_root)
        if leased.is_err:
            _log.error("pool-lease failed: %s", leased.danger_err.value)
            sys.exit(1)
        _log.info(str(leased.danger_ok.path))
        return

    if pool_cmd == "status":
        status = pool_status(repo_root)
        if status.is_err:
            _log.error("pool-status failed: %s", status.danger_err.value)
            sys.exit(1)
        for entry in status.danger_ok:
            _log.info("%d: %s ready=%s", entry.index, entry.path, entry.ready)
        return

    _log.error("frob scaffold pool requires a subcommand (warm/lease/status)")
    sys.exit(1)


# frob:doc docs/modules/app.md#runners
# frob:doc docs/guides/worktree-pool.md#cli-frob-scaffold-pool-t-0877
# frob:ticket T-0736
# frob:tests tests/system/test_cli_scaffold_apply.py::TestScaffoldApplyCli.test_apply_reports_changes  # noqa: E501
def run(cfg: AppConfig) -> None:
    cmd = cfg.scaffold_command
    if cmd in ("list", None):
        for t in list_project_types():
            _log.info(t)
        return

    if cmd == "apply":
        result = apply_managed_blocks(Path("."))
        if result.is_err:
            _log.error(result.danger_err.value)
            sys.exit(1)
        for line in result.danger_ok:
            _log.info(line)
        return

    if cmd == "pool":
        _run_pool(cfg)
        return

    proj_type = cfg.scaffold_type
    proj_name = cfg.scaffold_name

    if proj_type is None or proj_name is None:
        _log.error("frob scaffold new requires <type> and <name>")
        sys.exit(1)

    out_dir = cfg.scaffold_output or Path(".")
    force = cfg.scaffold_force
    result = render_project(proj_type, proj_name, out_dir, force=force)

    if result.is_err:
        _log.error(result.danger_err.value)
        sys.exit(1)

    for p in result.danger_ok:
        _log.info("created %s", p)
