from __future__ import annotations

import logging
import logging.config
import os
import sys
import tomllib
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.toml"
_initialized = False

# see T-2979 for the history behind this
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


# frob:ticket T-3570
def _is_vet_hook_mode() -> bool:
    """True for `frob vet --hook '<command>'` (T-3438's own machine-
    consumed shape) -- checked via a direct `sys.argv` scan, the same
    ordering-independent pattern `_resolve_stdout_level_override` above
    already uses and for the identical reason: `_init` can fire from a
    module-level `get_logger(__name__)` reached before `frob.__main__.
    main` runs its own argv-based dispatch, and `_initialized` caches
    permanently on first call."""
    return "vet" in sys.argv and "--hook" in sys.argv


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
def _init() -> None:
    global _initialized
    if _initialized:
        return
    with _CONFIG_PATH.open("rb") as f:
        cfg = tomllib.load(f)
    # frob:waive SEC110 reason="FROB_FORCE_LOG_HANDLERS is a boolean test-harness \
    # opt-in, not a secret"
    if _under_pytest() and os.environ.get(_FORCE_HANDLERS_ENV_VAR) != "1":
        # see T-1621 for the history behind this
        cfg["root"]["handlers"] = []
    logging.config.dictConfig(cfg)
    _initialized = True
    # T-2979: apply the FROB_LOG_LEVEL override (if any) AFTER dictConfig
    # so it wins over config.toml's default -- this is the single place
    # every entry point (CLI dispatch, direct library import, a test)
    # converges on, so the override applies regardless of which `frob`
    # subcommand or code path runs first.
    _apply_stdout_level_override()
    _suppress_stderr_warnings_in_vet_hook_mode()


# frob:ticket T-3570
def _apply_stdout_level_override() -> None:
    """Apply the `FROB_LOG_LEVEL`/`-v`/`--verbose` override (if any) to
    the `stdout` handler -- split out of `_init` (T-3570/ARCH001) so
    that function stays under the long-AND-complex threshold. Must run
    AFTER `dictConfig` so it wins over `config.toml`'s default."""
    override = _resolve_stdout_level_override()
    if override is not None:
        from frob.logging.handler import _LazyStdoutHandler

        for handler in logging.getLogger().handlers:
            if isinstance(handler, _LazyStdoutHandler):
                handler.setLevel(override)


# frob:ticket T-3570
def _suppress_stderr_warnings_in_vet_hook_mode() -> None:
    """`frob vet --hook ...`'s stdout/exit-code contract (this
    module's own docstring) is machine-consumed by a Claude Code
    PreToolUse hook -- it must emit NOTHING beyond that contract, the
    same "no leakage onto a machine-consumed stream" requirement
    T-3438 already enforces for the startup-nag PRINTS in `frob.
    __main__`. That fix only covered the nags; it did not stop an
    ordinary WARNING-level log record (e.g. a routine, expected-per-
    call platform-detection miss) from reaching the `stderr` handler
    via the normal logging path. Raise the `stderr` handler's
    threshold above WARNING in hook mode specifically -- ERROR and
    above still surface (a genuine failure worth an operator's
    attention), and `_run_hook`'s own deliberate BLOCK message
    (`vet_runner.py`) writes to `sys.stderr` directly via `print`,
    never through this logger, so it is unaffected. Split out of
    `_init` (T-3570/ARCH001) so that function stays under the long-
    AND-complex threshold."""
    if not _is_vet_hook_mode():
        return
    from frob.logging.handler import _LazyStderrHandler

    for handler in logging.getLogger().handlers:
        if isinstance(handler, _LazyStderrHandler):
            handler.setLevel(logging.ERROR)


# frob:doc docs/modules/logging.md#public-api
def get_logger(name: str) -> logging.Logger:
    _init()
    return logging.getLogger(name)
