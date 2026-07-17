from __future__ import annotations

import contextlib
import logging
import sys
from collections.abc import Iterator
from pathlib import Path

from frob.app.config import AppConfig
from frob.check import detect_project_type, run_check, run_check_cpp, run_check_rust
from frob.logging import get_logger

_log = get_logger(__name__)


@contextlib.contextmanager
def _quiet_stdout_logs() -> Iterator[None]:
    """Temporarily silence INFO/DEBUG logging to stdout.

    `--json` output must be pure JSON on stdout; library modules invoked by a
    check stage (e.g. `frob.gates.run_gates`) log liberally at INFO/DEBUG per
    this project's logging convention, which would otherwise interleave with
    (and corrupt) the final JSON payload."""
    root_logger = logging.getLogger()
    stdout_handlers = [
        h
        for h in root_logger.handlers
        if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout
    ]
    saved = [h.level for h in stdout_handlers]
    for h in stdout_handlers:
        h.setLevel(logging.WARNING)
    try:
        yield
    finally:
        for h, level in zip(stdout_handlers, saved, strict=True):
            h.setLevel(level)


def run(cfg: AppConfig) -> None:
    root = cfg.check_path or Path(".")

    if not root.exists():
        _log.error("path does not exist: %s", root)
        sys.exit(1)

    if cfg.check_stamp_coverage:
        from frob.gates import stamp_coverage

        result = stamp_coverage(root)
        if result.is_err:
            _log.error("stamp-coverage failed: %s", result.danger_err)
            sys.exit(1)
        _log.info("coverage stamp written")
        return

    project_type = cfg.check_type or detect_project_type(root)

    _ctx = _quiet_stdout_logs() if cfg.check_json else contextlib.nullcontext()

    with _ctx:
        if project_type == "cpp":
            result = run_check_cpp(
                root,
                build_dir=cfg.check_build_dir,
                skip_build=cfg.check_skip_build,
                skip_clang_tidy=cfg.check_skip_clang_tidy,
                skip_clang_format=cfg.check_skip_clang_format,
                skip_tests=cfg.check_skip_tests,
                valgrind=cfg.check_valgrind,
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
                skip_gates=cfg.check_skip_gates,
                only=frozenset(cfg.check_only) if cfg.check_only else None,
                ticket=cfg.check_ticket,
                base=cfg.check_base,
            )

    if cfg.check_json:
        _log.info(result.as_json())
    else:
        _log.info(result.as_text())

    if result.total_errors > 0:
        sys.exit(1)
