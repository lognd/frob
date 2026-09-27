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
import os
import shlex
import sys
from collections.abc import Iterator
from pathlib import Path

from frob.logging import get_logger
from frob.logging.handler import _LazyStderrHandler, _LazyStdoutHandler
from frob.render import Renderer
from frob.tickets._worktree_guard import FROB_WORKTREE_ENV, agent_env_exports

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
    """Argument parser for `frob agent`. `agent` has two children -- `env`
    (bare `frob agent [path]` dispatches straight to it, T-4546, same
    flattening `frob claude`/`frob natives` got, T-4522) and `brief`
    (T-draft-df99eb2d, always named explicitly: `frob agent brief
    <ticket>`, no bare-`agent` implication). The two-word `frob agent env
    [path]` spelling is kept working as a documented alias for one
    release. `run` (below) normalizes `argv` to insert the implied `env`
    token BEFORE parsing -- a `path` positional cannot be mirrored
    directly onto the group parser the way T-4522 mirrored `claude`/
    `natives`' own optional FLAGS, because a bare positional here would
    collide with `add_subparsers`' own positional slot (argparse tries to
    match the first token as a subcommand name first, so `frob agent
    /some/path` would otherwise fail with "invalid choice:
    '/some/path'")."""
    p = argparse.ArgumentParser(
        prog="frob agent",
        description="Print/export the dispatched-agent guard env for a "
        "worktree. 'env' is implied (T-4546): bare `frob agent` runs it; "
        "the two-word `frob agent env` spelling is kept working as a "
        "documented alias for one release. `brief <ticket>` (T-draft-"
        "df99eb2d) prints the dispatch brief for one ticket instead.",
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
        help="worktree path to resolve (default: cwd, also the default "
        "action for bare `frob agent`, T-4546)",
    )
    # frob:ticket T-draft-df99eb2d
    brief_p = agent_sub.add_parser(
        "brief",
        help="print the dispatch brief for one ticket "
        "(playbook contract + ledger fields, T-draft-df99eb2d)",
    )
    brief_p.add_argument("ticket", help="ticket id to brief")
    brief_p.add_argument(
        "--path",
        dest="path",
        default=".",
        metavar="DIR",
        help="repo root to resolve the ledger/playbook against (default: cwd)",
    )
    return p


# frob:ticket T-4546
# frob:ticket T-draft-df99eb2d
def _normalize_agent_argv(argv: list[str]) -> list[str]:
    """Insert the implied `env` subcommand token ahead of `argv` when it is
    missing (T-4546): a bare `frob agent [path]` must run what `frob
    agent env [path]` ran. `brief` (T-draft-df99eb2d) is NEVER implied --
    it always requires its own explicit token, since a bare `frob agent`
    has meant `env` since T-4546 and silently reinterpreting it as `brief`
    depending on the next token's shape would be a surprise, not a
    convenience. Leaves `argv` untouched when the first token already IS
    `env`, `brief`, or is a help flag -- all three must reach
    `_build_agent_parser` unmodified so argparse's own `--help`/usage
    handling stays exactly as it always has."""
    if argv and argv[0] not in ("env", "brief", "-h", "--help"):
        return ["env", *argv]
    return argv or ["env"]


def _force_utf8_stdout() -> None:
    """T-4446: reconfigure `sys.stdout` to UTF-8 (text-mode, so `print`/
    `Renderer` keep working unchanged), regardless of the interpreter's
    inherited console code page or `PYTHONIOENCODING`. `frob agent env`'s
    whole output contract is "pure ASCII shell, `eval`-able" -- but on the
    GitHub Windows runner, `sys.stdout`'s default encoding can resolve to
    UTF-16 (console code page / `PYTHONIOENCODING` interaction), so a
    plain `print("export ...")` writes UTF-16 code units, interleaving a
    NUL byte after every ASCII byte. Bash's `eval "$(...)"` reads that as
    garbage (the exact CI failure this fixes: NUL-interleaved bytes in
    the captured `frob agent env` output). `TextIOWrapper.reconfigure`
    (py3.7+) is the one supported way to change the encoding of the
    ALREADY-BOUND `sys.stdout` object in place, so every other caller of
    this module (logging's `_LazyStdoutHandler`, any other write to the
    same stream) is unaffected -- this is called only in `_run_env`'s own
    narrow window, not at import time or module scope. Silently no-ops if
    `sys.stdout` is something that does not support `reconfigure` (e.g. a
    test harness's `io.StringIO` stand-in) rather than crashing a command
    whose whole job is to never break the caller's shell."""
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if reconfigure is not None:
        reconfigure(encoding="utf-8", errors="strict", newline="\n")


# frob:waive ARCH103 reason="report-and-exit CLI helper (frob agent env's one \
# subcommand body): resolve exports, add the T-4459 PYTHONPATH line, print -- \
# splitting the print loop from the export-building it prints would separate an \
# operation from the one caller that uses it, not reduce real complexity, matching \
# bind_runner.py's identical posture"
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
    resolve to a git worktree at all. T-4446: forces `sys.stdout` to
    UTF-8 first (`_force_utf8_stdout`) so the exported bytes are always
    plain ASCII/UTF-8 shell, never UTF-16, regardless of the runner's
    console code page.

    T-4459: also exports `PYTHONPATH=<resolved worktree>/src` whenever
    that directory exists, AHEAD of anything else the caller's shell
    already carries (`shlex.quote`d, `:`-joined with any inherited
    `PYTHONPATH` so an existing value is extended, not clobbered) -- a
    worktree test run through the root checkout's own interpreter
    otherwise silently imports `frob` from the ROOT src/ (its editable
    install's `.pth` wins over an unset `PYTHONPATH`), measuring main's
    code instead of the branch under test. This is deliberately NOT part
    of `agent_env_exports` itself (that function's contract is
    `FROB_WORKTREE`/`FROB_AGENT`/xdist-worker env, and its own tests
    assert an exact export-key set); the PYTHONPATH line is `frob agent
    env`'s own CLI-level addition, same as this function already owns
    `_force_utf8_stdout`."""
    _force_utf8_stdout()
    with _all_logs_to_stderr():
        result = agent_env_exports(Path(path))
        if result.is_err:
            _log.error(
                "frob agent env: %s does not resolve to a git worktree (%s)",
                path,
                result.danger_err.value,
            )
            sys.exit(1)
        exports = dict(result.danger_ok)
        worktree_root = Path(exports[FROB_WORKTREE_ENV])
        worktree_src = worktree_root / "src"
        if worktree_src.is_dir():
            # frob:waive SEC110 reason="PYTHONPATH is a path-list env var, never a \
            # secret -- same posture as _worktree_guard.py's own FROB_WORKTREE_ENV \
            # reads"
            inherited = os.environ.get("PYTHONPATH", "")
            pythonpath = (
                f"{worktree_src}:{inherited}" if inherited else str(worktree_src)
            )
            exports["PYTHONPATH"] = pythonpath
            _log.info(
                "agent env: exporting PYTHONPATH=%s (worktree src/, T-4459)",
                pythonpath,
            )
        renderer = Renderer.for_stream(sys.stdout)
        for key, value in exports.items():
            renderer.line(f"export {key}={shlex.quote(value)}")


# frob:ticket T-draft-df99eb2d
def _run_brief(ticket_id: str, path: str) -> None:
    """`frob agent brief <ticket> [--path DIR]` (T-draft-df99eb2d): resolve
    `path`'s (default cwd) repo root, render `frob.agent.render_agent_
    brief`'s dispatch brief for `ticket_id`, and print it to stdout.
    Exits 1 with a logged error when the ticket does not resolve (mirrors
    `_run_env`'s exit-1-on-resolve-failure posture)."""
    from pathlib import Path

    # frob:waive SYS003 reason="frob.agent is an intra-cli helper, owned by cli's own \
    # code= glob (design/frob.strata, src/frob/app/**) same as frob.app.agent_runner \
    # -- src/frob/agent/** belongs on that glob list too (T-draft-6d585d1b tracks \
    # adding it); this import is permanently intra-cli, not a cross-component edge"
    from frob.agent import render_agent_brief

    result = render_agent_brief(Path(path), ticket_id)
    if result.is_err:
        _log.error(
            "frob agent brief: %s failed under %s (%s)",
            ticket_id,
            path,
            result.danger_err.value,
        )
        sys.exit(1)
    renderer = Renderer.for_stream(sys.stdout)
    renderer.line(result.danger_ok)


# frob:doc docs/modules/app.md#runners
def run(argv: list[str]) -> None:
    """`frob agent [subcommand]` entry point (T-0574), dispatched directly
    by `__main__._dispatch` the same way `frob bind` is. `agent` has two
    children: `env` (bare/missing subcommand runs it too, T-4546 --
    `_normalize_agent_argv` inserts the implied token before parsing; the
    two-word `frob agent env` spelling still works as a documented alias
    for one release) and `brief` (T-draft-df99eb2d, always explicit)."""
    parser = _build_agent_parser()
    args = parser.parse_args(_normalize_agent_argv(argv))
    if args.agent_command == "env":
        _run_env(args.path)
        return
    if args.agent_command == "brief":
        _run_brief(args.ticket, args.path)
        return
    parser.print_help(sys.stderr)
    sys.exit(1)


__all__ = ["run"]
