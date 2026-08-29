from __future__ import annotations

import logging
import logging.config
import os
import sys
import tomllib
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.toml"
_initialized = False

# T-2979: the documented escape hatch back to full DEBUG chatter
# (`gitio: spawning ...`, `process: spawning ...`, `tickets: v2 index
# cache hit`, `is_baseline_stale: ...` and friends) -- see also `frob`'s
# global `-v`/`--verbose` flag, which sets `FROB_VERBOSE` before any
# logger is first touched (src/frob/__main__.py). `FROB_VERBOSE=1` is
# reused deliberately rather than inventing a second knob: T-2582 already
# wired it through `frob.logging.quiet.quiet_query_stdout` as the escape
# hatch for 8 human-mode query runners (debt/deprecated/exports/fleet/
# gitlog/mutate/outline/xref), which unconditionally suppress stdout-bound
# INFO/DEBUG to WARNING otherwise -- `-v` needs to disarm THAT suppression
# too, not just raise the base handler level, or it would restore
# nothing for any of those 8 commands. `FROB_LOG_LEVEL=<name>` is also
# read, for a caller who wants a specific level (e.g. `INFO`) rather than
# the `-v` default of full `DEBUG`.
_VERBOSE_ENV_VAR = "FROB_VERBOSE"
_LOG_LEVEL_ENV_VAR = "FROB_LOG_LEVEL"
# T-3263: opt-in escape hatch for a test that deliberately wants frob's OWN
# formatted stderr/stdout bytes even inside a pytest process (asserted via
# `capsys`, not `caplog`) -- e.g. a formatter-level regression guard for the
# "WARNING: " level prefix (docs/modules/logging.md's `_FrobFormatter`
# contract). `_under_pytest()`'s handlers=[] (T-1621) stays the default for
# every other test: this only flips when a test explicitly sets the env var
# itself (via `monkeypatch`, so it is unset again for every other test in
# the session), so the T-1621 double-reporting fix is untouched for the
# suite at large.
_FORCE_HANDLERS_ENV_VAR = "FROB_FORCE_LOG_HANDLERS"


def _resolve_stdout_level_override() -> int | None:
    """Resolve the stdout handler's DEBUG-chatter override level from
    `-v`/`--verbose` in `sys.argv`, `FROB_VERBOSE=1` (-> DEBUG, same
    effect), or `FROB_LOG_LEVEL=<name>` (an explicit level name); `None`
    if none apply -- an unrecognized `FROB_LOG_LEVEL` value is a silent
    no-op, not a crash, since this runs before any diagnostic channel
    exists to report a malformed env var through.

    `sys.argv` is checked directly here, NOT via `frob.__main__`'s own
    argument parsing (T-2979): `_init` can fire from a module-level
    `get_logger(__name__)` call reached by an import chain BEFORE
    `frob.__main__.main` ever runs its own argv scan -- `_init` caches
    `_initialized` permanently on first call, so a later env-var write
    from `main` would already be too late. `sys.argv` itself is populated
    by the interpreter before any user code runs at all, so reading it
    directly here is the only ordering-independent source of truth."""
    if "-v" in sys.argv or "--verbose" in sys.argv:
        return logging.DEBUG
    # frob:waive SEC110 reason="FROB_VERBOSE is a boolean logging-verbosity flag, not \
    # a secret"
    if os.environ.get(_VERBOSE_ENV_VAR) == "1":
        return logging.DEBUG
    # frob:waive SEC110 reason="FROB_LOG_LEVEL names a stdlib logging level \
    # (DEBUG/INFO/...), not a secret"
    raw = os.environ.get(_LOG_LEVEL_ENV_VAR)
    if not raw:
        return None
    level = logging.getLevelName(raw.strip().upper())
    return level if isinstance(level, int) else None


def _under_pytest() -> bool:
    """True inside a pytest process (T-1621), used to skip installing
    frob's own root StreamHandlers there.

    Checked via `"pytest" in sys.modules` rather than the per-test
    `PYTEST_CURRENT_TEST` env var: frob's own loggers are typically first
    created at COLLECTION time (many modules call `get_logger(__name__)`
    at import time, before any test has started and before pytest sets
    that env var), while pytest itself is already imported by the time
    ANY test module is collected -- `sys.modules` is the check that is
    true for the whole session, not just mid-test."""
    return "pytest" in sys.modules


# frob:ticket T-3263
# frob:tests tests/system/test_cli_check.py::TestGitlessTargetGateSeverity.test_render_lint_gate_warns_not_errors_on_gitless_root  # noqa: E501
def _init() -> None:
    global _initialized
    if _initialized:
        return
    with _CONFIG_PATH.open("rb") as f:
        cfg = tomllib.load(f)
    # frob:waive SEC110 reason="FROB_FORCE_LOG_HANDLERS is a boolean test-harness \
    # opt-in, not a secret"
    if _under_pytest() and os.environ.get(_FORCE_HANDLERS_ENV_VAR) != "1":
        # T-1621: every record frob logs was appearing TWICE in pytest's
        # own report, in two different formats -- not two copies from one
        # handler, but ONE record reaching the terminal via two
        # INDEPENDENT reporters that both sit on the root logger. Path 1:
        # frob's own `_LazyStderrHandler`/`_LazyStdoutHandler` (below)
        # write a frob-formatted line straight to `sys.stderr`/`sys.
        # stdout`, which pytest's output capturing reports back verbatim
        # as "Captured stderr/stdout call". Path 2: pytest's OWN logging-
        # capture plugin attaches its own `LogCaptureHandler` directly to
        # the root logger for the duration of every test (unconditionally,
        # regardless of `log_cli`/dictConfig -- this repo's own dictConfig
        # neither installs nor could remove it), and reports the SAME
        # record again as "Captured log call" in pytest's own default
        # format. Root's own handler list is left empty here rather than
        # setting `propagate = False`: `propagate` must stay on so path 2
        # (which does not depend on frob's own handlers at all) keeps
        # working for `caplog`-based tests, and so a downstream consumer
        # of this library who attaches their OWN handler above frob's
        # loggers still receives every record -- only frob's OWN
        # stdout/stderr handlers are skipped, and only under pytest, where
        # path 2 already reports every record on its own.
        cfg["root"]["handlers"] = []
    logging.config.dictConfig(cfg)
    _initialized = True
    # T-2979: apply the FROB_LOG_LEVEL override (if any) AFTER dictConfig
    # so it wins over config.toml's default -- this is the single place
    # every entry point (CLI dispatch, direct library import, a test)
    # converges on, so the override applies regardless of which `frob`
    # subcommand or code path runs first.
    override = _resolve_stdout_level_override()
    if override is not None:
        from frob.logging.handler import _LazyStdoutHandler

        for handler in logging.getLogger().handlers:
            if isinstance(handler, _LazyStdoutHandler):
                handler.setLevel(override)


# frob:doc docs/modules/logging.md#public-api
def get_logger(name: str) -> logging.Logger:
    _init()
    return logging.getLogger(name)
