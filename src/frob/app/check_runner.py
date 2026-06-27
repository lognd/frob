from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.check import detect_project_type, run_check, run_check_cpp, run_check_rust
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    root = cfg.check_path or Path(".")

    project_type = cfg.check_type or detect_project_type(root)

    if project_type == "cpp":
        result = run_check_cpp(
            root,
            build_dir=cfg.check_build_dir,
            skip_build=cfg.check_skip_build,
            skip_clang_tidy=cfg.check_skip_clang_tidy,
            skip_clang_format=cfg.check_skip_clang_format,
            skip_tests=cfg.check_skip_tests,
            valgrind=cfg.check_valgrind,
            pycharm_path=cfg.check_pycharm,
        )
    elif project_type == "rust":
        result = run_check_rust(
            root,
            skip_check=cfg.check_skip_cargo_check,
            skip_clippy=cfg.check_skip_clippy,
            skip_fmt=cfg.check_skip_fmt,
            skip_tests=cfg.check_skip_tests,
            valgrind=cfg.check_valgrind,
        )
    else:
        # Python (default)
        result = run_check(
            root,
            skip_ruff=cfg.check_skip_ruff,
            skip_ty=cfg.check_skip_ty,
            skip_arch=cfg.check_skip_arch,
            skip_cycle=cfg.check_skip_cycle,
            skip_dup=cfg.check_skip_dup,
            skip_bind=cfg.check_skip_bind,
            skip_exports=cfg.check_skip_exports,
            pycharm_path=cfg.check_pycharm,
        )

    if cfg.check_json:
        _log.info(result.as_json())
    else:
        _log.info(result.as_text())

    if result.total_errors > 0:
        sys.exit(1)
