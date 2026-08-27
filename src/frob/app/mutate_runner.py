"""CLI wiring for `frob mutate` -- mutation testing (T-0011)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.logging.quiet import quiet_query_stdout
from frob.render import Renderer
from frob.tickets._worktree_guard import apply_agent_env, warn_if_xdist_bound_missing

_log = get_logger(__name__)


# frob:ticket T-0011
# frob:ticket T-0562
# frob:ticket T-0815
# frob:ticket T-0588
# frob:ticket T-3099
# frob:doc docs/modules/app.md#runners
# frob:tests tests/unit/test_app_runners.py::TestMutateRunner.test_success_no_survivors_text_mode  # noqa: E501
# frob:tests tests/unit/test_pytest_spawn_env_wiring.py::TestMutateRunnerWiring.test_must_fire_applies_and_warns_before_run_mutations  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Mutate a file and report which mutants survived the test command.

    T-0815/T-2582: `run_mutations` spawns the mutant test command through
    `guarded_subprocess_run`, which DEBUG-logs every spawn -- and this
    repo's stdout log handler is DEBUG-level by default, so an unguarded
    call here would leak that line into either mode's output. Quieted in
    BOTH modes now (`FROB_VERBOSE=1` opts back into the diagnostic
    lines); human mode used to keep them always visible."""
    from frob.mutate import run_mutations

    if cfg.mutate_file is None:
        _log.error("frob mutate requires a <file>")
        sys.exit(1)
    root = (cfg.mutate_path or Path(".")).resolve()
    # Everything after `--` is the test command; default to the file's
    # touched-set tests via `frob test`.
    argv = tuple(cfg.mutate_argv) or ("uv", "run", "pytest", "-q")

    # T-3099: apply the T-3094 fleet-aware xdist bound in-process before
    # `run_mutations` below spawns the mutant test command, so a default
    # `pytest -q` mutant run inherits it directly; warn loudly if a fleet
    # context exists but the bound did not make it into this process's env.
    apply_agent_env(root)
    warn_if_xdist_bound_missing(root)

    with quiet_query_stdout():
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
