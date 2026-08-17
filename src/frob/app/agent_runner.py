"""CLI wiring for `frob agent` (T-0574): mechanically inject the guard env
a dispatched worktree agent's shell needs, instead of relying on playbook
prose to remember it by hand.

Wired the same way `frob bind` is (see `frob.app.bind_runner`): `run(argv)`
takes the raw sub-argv and owns its own parser, bypassing the
`AppConfig`/`Subcommand` dispatch table entirely -- `frob agent` has no
ticket/graph state to load and no reason to route through `App`, so adding
it there would mean touching `src/frob/app/config.py` and
`src/frob/app/app.py` for a command that is really just "resolve a path
and print two env lines," which is exactly `bind`'s own precedent for
staying self-contained.
"""

from __future__ import annotations

import argparse
import contextlib
import logging
import shlex
import sys
from collections.abc import Iterator
from pathlib import Path

from frob.logging import get_logger
from frob.logging.handler import _LazyStderrHandler, _LazyStdoutHandler
from frob.render import Renderer
from frob.tickets._worktree_guard import agent_env_exports

_log = get_logger(__name__)


@contextlib.contextmanager
def _all_logs_to_stderr() -> Iterator[None]:
    """Route every log record -- regardless of level -- to stderr for the
    duration of the block, leaving stdout untouched by logging entirely.

    `frob agent env`'s whole purpose is to be `eval`'d
    (`eval "$(uv run frob agent env <path>)"`); its stdout MUST contain
    only the `export ...` lines `_run_env` prints below. The shared
    `config.toml` root logger normally splits DEBUG/INFO to stdout and
    WARNING+ to stderr (`_LazyStdoutHandler`/`_LazyStderrHandler`), which
    is right for every other subcommand but fatal here -- `gitio`/
    `process` tracing that `agent_env_exports` triggers (git subprocess
    spawns resolving the worktree root) prints plain-text lines like
    `gitio: spawning ('git', ...)` straight onto the same stdout the
    caller is about to `eval`, producing a bash syntax error at the
    literal `(` (T-2259). Muting those records outright (raising the
    stdout handler's level, `quiet_stdout_logs`'s approach) would satisfy
    the syntax-error symptom but silently drop diagnostics that are
    load-bearing elsewhere; this instead disables the stdout handler and
    widens the stderr handler to accept every level, so the same records
    still appear, just on the channel this command was never polluting.
    Scoped to this one subcommand (not a global logging config change):
    every other command keeps the normal stdout/stderr split."""
    root = logging.getLogger()
    stdout_handlers = [h for h in root.handlers if isinstance(h, _LazyStdoutHandler)]
    stderr_handlers = [h for h in root.handlers if isinstance(h, _LazyStderrHandler)]
    saved_stdout_levels = [h.level for h in stdout_handlers]
    saved_stderr_levels = [h.level for h in stderr_handlers]
    for h in stdout_handlers:
        h.setLevel(logging.CRITICAL + 1)
    for h in stderr_handlers:
        h.setLevel(logging.DEBUG)
    try:
        yield
    finally:
        for h, level in zip(stdout_handlers, saved_stdout_levels, strict=True):
            h.setLevel(level)
        for h, level in zip(stderr_handlers, saved_stderr_levels, strict=True):
            h.setLevel(level)


def _build_agent_parser() -> argparse.ArgumentParser:
    """Argument parser for `frob agent`."""
    p = argparse.ArgumentParser(
        prog="frob agent",
        description="Print/export the dispatched-agent guard env for a worktree",
    )
    agent_sub = p.add_subparsers(dest="agent_command")
    env_p = agent_sub.add_parser(
        "env",
        help=("print FROB_WORKTREE/FROB_AGENT export lines for a worktree (T-0574)"),
    )
    env_p.add_argument(
        "path",
        nargs="?",
        default=".",
        help="worktree path to resolve (default: cwd)",
    )
    return p


def _run_env(path: str) -> None:
    """`frob agent env [path]`: resolve `path`'s (default cwd) worktree
    root and print `export FROB_WORKTREE=...` / `export FROB_AGENT=1`
    lines to stdout, eval-able the same way `ssh-agent -s` output is
    (`eval "$(frob agent env)"`) -- dispatch tooling can inject the guard
    env mechanically instead of a coordinator hand-setting it or a
    playbook telling an agent to remember it. Each value is `shlex.quote`d
    before printing so a worktree path containing a space/quote/shell
    metacharacter cannot break the `eval` (or worse, get interpreted as a
    second command). Exits 1 with a logged error if `path` does not
    resolve to a git worktree at all."""
    with _all_logs_to_stderr():
        result = agent_env_exports(Path(path))
        if result.is_err:
            _log.error(
                "frob agent env: %s does not resolve to a git worktree (%s)",
                path,
                result.danger_err.value,
            )
            sys.exit(1)
        exports = result.danger_ok
        renderer = Renderer.for_stream(sys.stdout)
        for key, value in exports.items():
            renderer.line(f"export {key}={shlex.quote(value)}")


# frob:doc docs/modules/app.md#runners
# frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_prints_export_lines_for_worktree  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_defaults_to_cwd  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_non_repo_path_exits_nonzero  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestAgentEnvStdoutPurity.test_bare_eval_succeeds_with_no_filtering  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestAgentEnvStdoutPurity.test_stdout_contains_only_export_lines  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestAgentEnvStdoutPurity.test_diagnostics_still_appear_on_stderr  # noqa: E501
# frob:tests tests/test_worktree_guard.py::TestAgentEnvStdoutPurity.test_no_fleet_context_still_produces_valid_eval_output  # noqa: E501
def run(argv: list[str]) -> None:
    """`frob agent <subcommand>` entry point (T-0574), dispatched directly
    by `__main__._dispatch` the same way `frob bind` is. The implemented
    subcommand surface today is `env`; an unrecognized/missing subcommand
    falls through to argparse's own usage error."""
    parser = _build_agent_parser()
    args = parser.parse_args(argv)
    if args.agent_command == "env":
        _run_env(args.path)
        return
    parser.print_help(sys.stderr)
    sys.exit(1)


__all__ = ["run"]
