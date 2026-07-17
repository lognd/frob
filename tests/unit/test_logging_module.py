"""Unit tests for frob.logging: get_logger, filters, color helpers, quiet_stdout_logs."""

from __future__ import annotations

import logging
import sys

from frob.logging import get_logger, quiet_stdout_logs
from frob.logging.color import paint, should_color
from frob.logging.filter import BelowLevelFilter


def test_get_logger_returns_named_logger():
    # frob:tests src/frob/logging/logger.py::get_logger kind="unit"
    log = get_logger("frob.test.example")
    assert isinstance(log, logging.Logger)
    assert log.name == "frob.test.example"


def test_below_level_filter():
    # frob:tests src/frob/logging/filter.py::BelowLevelFilter.filter kind="unit"
    f = BelowLevelFilter("WARNING")
    info_record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", (), None)
    warn_record = logging.LogRecord("x", logging.WARNING, __file__, 1, "msg", (), None)
    assert f.filter(info_record) is True
    assert f.filter(warn_record) is False


def test_should_color_respects_no_color(monkeypatch):
    # frob:tests src/frob/logging/color.py::should_color kind="unit"
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_color() is False


def test_should_color_respects_force_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert should_color() is True


def test_paint_wraps_when_enabled():
    # frob:tests src/frob/logging/color.py::paint kind="unit"
    result = paint("hi", "31", enabled=True)
    assert result == "\x1b[31mhi\x1b[0m"


def test_paint_verbatim_when_disabled():
    assert paint("hi", "31", enabled=False) == "hi"


def test_quiet_stdout_logs_raises_and_restores_level():
    # frob:tests src/frob/logging/quiet.py::quiet_stdout_logs kind="unit"
    root = logging.getLogger()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    root.addHandler(handler)
    try:
        assert handler.level == logging.DEBUG
        with quiet_stdout_logs():
            assert handler.level == logging.WARNING
        assert handler.level == logging.DEBUG
    finally:
        root.removeHandler(handler)
