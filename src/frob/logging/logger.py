from __future__ import annotations

import logging
import logging.config
import sys
import tomllib
from pathlib import Path

_CONFIG_PATH = Path(__file__).parent / "config.toml"
_initialized = False


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


def _init() -> None:
    global _initialized
    if _initialized:
        return
    with _CONFIG_PATH.open("rb") as f:
        cfg = tomllib.load(f)
    if _under_pytest():
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


# frob:doc docs/modules/logging.md#public-api
def get_logger(name: str) -> logging.Logger:
    _init()
    return logging.getLogger(name)
