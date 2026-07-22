"""CLI wiring for `frob mutate` -- mutation testing (T-0011)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0011
# frob:doc docs/modules/app.md#runners
def run(cfg: AppConfig) -> None:
    """Mutate a file and report which mutants survived the test command."""
    from frob.mutate import run_mutations

    if cfg.mutate_file is None:
        _log.error("frob mutate requires a <file>")
        sys.exit(1)
    root = (cfg.mutate_path or Path(".")).resolve()
    # Everything after `--` is the test command; default to the file's
    # touched-set tests via `frob test`.
    argv = tuple(cfg.mutate_argv) or ("uv", "run", "pytest", "-q")

    result = run_mutations(root, cfg.mutate_file, argv)
    if result.is_err:
        _log.error("frob mutate: %s", result.danger_err)
        sys.exit(1)
    report = result.danger_ok

    renderer = Renderer.for_stream(sys.stdout)
    if cfg.mutate_json:
        renderer.line(report.model_dump_json(indent=2))
    else:
        renderer.line(
            f"mutation score {report.score:.0%}  "
            f"({report.killed}/{report.total} killed)"
        )
        for m in report.survivors:
            renderer.line(f"  SURVIVOR {m.file}:{m.line}  {m.description}")
    if report.survivors:
        sys.exit(1)
