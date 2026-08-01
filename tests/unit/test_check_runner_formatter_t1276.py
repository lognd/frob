"""Direct-call coverage for `frob.app.check_runner._ColorizedLevelFormatter`
(T-1276).

`_ColorizedLevelFormatter.format` (T-0420) is only exercised today via a
subprocess CLI test (`tests/system/test_cli_check.py`), which pytest-cov
cannot attribute back to the running process -- hence its 0.0%-branch
TEST005 finding despite being behaviorally tested end to end. These tests
build a bare `logging.LogRecord` at each level (DEBUG/INFO passthrough,
WARNING yellow, ERROR red) and call `format()` directly against a
formatter with `color=True`, asserting the exact ANSI wrapping
`style_warn`/`style_fail` apply -- and one more with `color=False`
proving the non-TTY path emits the base text completely unchanged, per
the class's own docstring.
"""

from __future__ import annotations

import logging

from frob.app.check_runner import _ColorizedLevelFormatter


def _record(level: int, msg: str) -> logging.LogRecord:
    """A minimal `LogRecord` at `level` with message text `msg`."""
    return logging.LogRecord(
        name="frob.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )


class TestColorizedLevelFormatter:
    def test_debug_passes_through_unchanged(self) -> None:
        # frob:tests \
        # tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.\
        # test_debug_passes_through_unchanged
        fmt = _ColorizedLevelFormatter(logging.Formatter("%(message)s"), color=True)
        out = fmt.format(_record(logging.DEBUG, "debug line"))
        assert out == "debug line"

    def test_info_passes_through_unchanged(self) -> None:
        # frob:tests \
        # tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.\
        # test_info_passes_through_unchanged
        fmt = _ColorizedLevelFormatter(logging.Formatter("%(message)s"), color=True)
        out = fmt.format(_record(logging.INFO, "info line"))
        assert out == "info line"

    def test_warning_is_painted_yellow_when_color_on(self) -> None:
        # frob:tests \
        # tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.\
        # test_warning_is_painted_yellow_when_color_on
        fmt = _ColorizedLevelFormatter(logging.Formatter("%(message)s"), color=True)
        out = fmt.format(_record(logging.WARNING, "warn line"))
        assert out != "warn line"
        assert "warn line" in out
        assert out.startswith("\x1b[")

    def test_error_is_painted_red_when_color_on(self) -> None:
        # frob:tests \
        # tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.\
        # test_error_is_painted_red_when_color_on
        fmt = _ColorizedLevelFormatter(logging.Formatter("%(message)s"), color=True)
        out = fmt.format(_record(logging.ERROR, "error line"))
        assert out != "error line"
        assert "error line" in out
        assert out.startswith("\x1b[")

    def test_error_is_unpainted_when_color_off(self) -> None:
        # frob:tests \
        # tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.\
        # test_error_is_unpainted_when_color_off
        fmt = _ColorizedLevelFormatter(logging.Formatter("%(message)s"), color=False)
        out = fmt.format(_record(logging.ERROR, "error line"))
        assert out == "error line"

    def test_critical_uses_the_error_branch_too(self) -> None:
        # frob:tests \
        # tests/unit/test_check_runner_formatter_t1276.py::TestColorizedLevelFormatter.\
        # test_critical_uses_the_error_branch_too
        # CRITICAL is >= logging.ERROR, so it must take the same red-paint
        # branch as ERROR itself (the `>=` comparison, not an `==`).
        fmt = _ColorizedLevelFormatter(logging.Formatter("%(message)s"), color=True)
        out = fmt.format(_record(logging.CRITICAL, "critical line"))
        assert "critical line" in out
        assert out.startswith("\x1b[")
