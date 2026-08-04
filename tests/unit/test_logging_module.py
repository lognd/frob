"""Unit tests for frob.logging: get_logger, filters, color helpers, quiet_stdout_logs."""

from __future__ import annotations

import io
import logging
import sys
from pathlib import Path

from frob.gates import coverage_gate
from frob.gitio import Diff
from frob.graph import build_graph
from frob.logging import get_logger, quiet_stdout_logs
from frob.logging.color import paint, should_color
from frob.logging.filter import _BelowLevelFilter
from frob.testing import CollectedTests
from frob.tickets import TicketQueue


def test_get_logger_returns_named_logger():
    # frob:tests src/frob/logging/logger.py::get_logger kind="unit"
    log = get_logger("frob.test.example")
    assert isinstance(log, logging.Logger)
    assert log.name == "frob.test.example"


# invariant spec: [INV-016](invariants/INV-016.md)
def test_below_level_filter():
    # frob:tests src/frob/logging/filter.py::_BelowLevelFilter.filter kind="unit"
    f = _BelowLevelFilter("WARNING")
    info_record = logging.LogRecord("x", logging.INFO, __file__, 1, "msg", (), None)
    warn_record = logging.LogRecord("x", logging.WARNING, __file__, 1, "msg", (), None)
    assert f.filter(info_record) is True
    assert f.filter(warn_record) is False


# invariant spec: [INV-037](invariants/INV-037.md)
def test_should_color_respects_no_color(monkeypatch):
    # frob:tests src/frob/logging/color.py::should_color kind="unit"
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_color() is False


def test_should_color_respects_force_color(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert should_color() is True


def test_should_color_no_color_wins_over_force_color(monkeypatch):
    # frob:tests src/frob/logging/color.py::should_color kind="unit"
    # frob:invariant INV-037
    # frob:ticket T-0585
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert should_color() is False


def test_should_color_term_dumb_disables_color_on_a_tty(monkeypatch):
    # frob:tests src/frob/logging/color.py::should_color kind="unit"
    # frob:invariant INV-037
    # frob:ticket T-0585
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setenv("TERM", "dumb")

    class _TtyStream(io.StringIO):
        """A StringIO whose `isatty()` reports True, unlike the real one."""

        def isatty(self) -> bool:
            return True

    assert should_color(_TtyStream()) is False


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


def test_lazy_handler_stream_properties_have_a_doc_edge(tmp_path):
    # frob:tests src/frob/gates/__init__.py::coverage_gate kind="unit"
    # frob:ticket T-1394
    # T-1394: _LazyStdoutHandler.stream/_LazyStderrHandler.stream each carry
    # a `frob:doc docs/modules/logging.md#public-api` comment already, but
    # the anchor's own describes list never named the `.stream` property
    # itself -- only the enclosing class -- so COV001 fired on both
    # properties despite the anchor "looking" present. Copies the real
    # repo's handler.py + logging.md verbatim (not a synthetic stand-in) so
    # this genuinely regresses if the describes entries are ever dropped.
    repo_root = Path(__file__).resolve().parents[2]
    handler_src = (repo_root / "src/frob/logging/handler.py").read_text()
    logging_doc = (repo_root / "docs/modules/logging.md").read_text()
    (tmp_path / "src" / "frob" / "logging").mkdir(parents=True)
    (tmp_path / "src" / "frob" / "logging" / "handler.py").write_text(handler_src)
    (tmp_path / "docs" / "modules").mkdir(parents=True)
    (tmp_path / "docs" / "modules" / "logging.md").write_text(logging_doc)
    snap = build_graph(tmp_path, tmp_path / ".frob" / "cache.db").danger_ok
    queue = TicketQueue(tickets={})
    diff = Diff(base="x", hunks=())
    tests = CollectedTests(node_ids=frozenset())
    violations = coverage_gate(tmp_path, snap, queue, diff, tests)
    stream_cov001 = [
        v
        for v in violations
        if v.rule == "COV001" and "Handler.stream" in v.message
    ]
    assert stream_cov001 == []
