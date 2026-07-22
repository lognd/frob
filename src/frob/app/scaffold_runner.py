from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.scaffold._managed import apply_managed_blocks
from frob.scaffold.project import list_project_types, render_project

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
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
