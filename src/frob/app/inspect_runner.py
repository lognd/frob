"""
frob inspect -- run PyCharm headless inspection and display results.

Usage:
    frob inspect [--pycharm PATH] [--profile PATH] [--output-dir DIR] [--scope DIR]
                 <project_dir>
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    from frob.inspect import find_pycharm, run_inspection
    from frob.process.parsers import parse_pycharm_dir

    project = cfg.inspect_project
    if project is None:
        _log.error("frob inspect requires <project_dir>")
        sys.exit(1)

    if not project.exists():
        _log.error("project directory does not exist: %s", project)
        sys.exit(1)

    # Resolve PyCharm binary
    pycharm = cfg.inspect_pycharm
    if pycharm is None:
        pycharm = find_pycharm()
    if pycharm is None:
        _log.error(
            "cannot find PyCharm inspect.bat -- use --pycharm PATH to specify it"
        )
        sys.exit(1)

    # Resolve profile
    profile = cfg.inspect_profile
    if profile is None:
        _log.error("--profile PATH is required (path to inspection profile XML)")
        sys.exit(1)

    if not profile.exists():
        _log.error("profile file does not exist: %s", profile)
        sys.exit(1)

    # Resolve output directory
    _tmp_dir = None
    if cfg.inspect_output_dir is not None:
        output_dir = cfg.inspect_output_dir
    else:
        _tmp_dir = tempfile.mkdtemp(prefix="frob_pycharm_")
        output_dir = Path(_tmp_dir)

    _log.info("output dir: %s", output_dir)

    success, err = run_inspection(
        pycharm,
        project,
        profile,
        output_dir,
        scope=cfg.inspect_scope,
    )

    if not success:
        assert err is not None
        _log.error("inspection failed: %s", err)
        sys.exit(1)

    result = parse_pycharm_dir(output_dir, project_root=project)

    if cfg.inspect_json:
        _log.info(result.as_json())
    else:
        _log.info(result.as_text())

    if result.error_count:
        sys.exit(1)
