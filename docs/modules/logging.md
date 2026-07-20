# frob logging

`frob.logging` is the module-logger setup every other frob module imports
`get_logger` from (never `print` for diagnostics, per the LOG EVERYTHING
convention). It centralizes the `dictConfig` init, a plain formatter, a
below-level filter for stdout, ANSI color helpers, and a context manager for
temporarily silencing stdout-bound log noise around `--json` output.

## Usage

<!-- frob:waive DOC004 reason="the symbols this block imports (get_logger, quiet_stdout_logs, paint, should_color) are each frob:describes-anchored in the Public API section immediately below -- DOC004's nearby-directive window only looks at preceding lines, not a following section, T-0436" -->

```python
from frob.logging import get_logger, quiet_stdout_logs
from frob.logging.color import paint, should_color

_log = get_logger(__name__)
_log.info("did the thing: %s", detail)
```

## Public API

<!-- frob:describes src/frob/logging/logger.py::get_logger -->
<!-- frob:describes src/frob/logging/formatter.py::_FrobFormatter -->
<!-- frob:describes src/frob/logging/formatter.py::_FrobFormatter.format -->
<!-- frob:describes src/frob/logging/filter.py::_BelowLevelFilter -->
<!-- frob:describes src/frob/logging/filter.py::_BelowLevelFilter.filter -->
<!-- frob:describes src/frob/logging/color.py::should_color -->
<!-- frob:describes src/frob/logging/color.py::paint -->
<!-- frob:describes src/frob/logging/quiet.py::quiet_stdout_logs -->
<!-- frob:describes src/frob/logging/quiet.py::stdout_log_level -->

```python
# frob/logging/logger.py
get_logger(name: str) -> logging.Logger
    # Lazily runs dictConfig from config.toml once, then returns a stdlib
    # logger for `name`; the one entry point every frob module uses.

# frob/logging/formatter.py
class FrobFormatter(logging.Formatter)
    # Plain formatter: INFO/DEBUG emit just the message, WARNING+ prefix
    # with the level name so errors are visible without relying on color.

FrobFormatter.format(record: logging.LogRecord) -> str
    # Renders one record per the show_level/severity rule above.

# frob/logging/filter.py
class BelowLevelFilter(logging.Filter)
    # A logging.Filter that only lets records strictly below a level
    # through, used to keep stdout free of WARNING+ noise.

BelowLevelFilter.filter(record: logging.LogRecord) -> bool
    # True if `record.levelno` is below the configured threshold.

# frob/logging/color.py
should_color(stream: IO[str] | None = None) -> bool
    # Decides whether ANSI color belongs on `stream` right now: NO_COLOR
    # wins if set, then FORCE_COLOR, then TTY-and-not-dumb-TERM. Every
    # CLI surface that wants color must call this rather than reimplementing
    # the precedence, or NO_COLOR handling desyncs across commands.

paint(text: str, code: str, enabled: bool = True) -> str
    # Wraps `text` in the SGR `code` ANSI escape when `enabled`, otherwise
    # returns it verbatim; pairs with should_color().

RED, GREEN, YELLOW, CYAN, BOLD, DIM
    # The SGR codes callers pass as paint()'s `code` argument; the only
    # palette frob's CLI output uses.

# frob/logging/quiet.py
quiet_stdout_logs() -> Iterator[None]
    # Context manager that raises stdout log handlers to WARNING for the
    # duration of the block, so a runner can print a --json payload to
    # stdout without INFO/DEBUG log lines corrupting it.

stdout_log_level(level: int) -> Iterator[None]
    # Context manager that sets stdout log handlers to an arbitrary level
    # for the duration of the block and restores it after; backs `frob
    # check`'s -v/-vv verbosity gating (WARNING default, INFO at -v, DEBUG
    # at -vv). Not reentrant/thread-safe like quiet_stdout_logs -- for a
    # single top-level CLI invocation, not concurrent library code.
```
