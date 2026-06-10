"""
arch_runner: run the architectural linter.

AppConfig fields used:
  arch_path (Path | None)  -- root directory to analyze (required)
  arch_json (bool)         -- emit JSON instead of plain text
  arch_max_function_lines (int | None)  -- override max lines per function
  arch_max_class_methods  (int | None)  -- override max methods per class
"""
from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger

_log = get_logger(__name__)


def run(cfg: AppConfig) -> None:
    from frob.arch import analyze_project

    root = getattr(cfg, "arch_path", None)
    if root is None:
        _log.error("frob arch requires <path>")
        sys.exit(1)

    kwargs: dict = {}
    max_fn = getattr(cfg, "arch_max_function_lines", None)
    if max_fn is not None:
        kwargs["max_function_lines"] = int(max_fn)
    max_cls = getattr(cfg, "arch_max_class_methods", None)
    if max_cls is not None:
        kwargs["max_class_methods"] = int(max_cls)

    result = analyze_project(root, **kwargs)

    use_json = getattr(cfg, "arch_json", False)
    if use_json:
        _log.info("%s", result.as_json())
    else:
        _log.info("%s", result.as_text())
