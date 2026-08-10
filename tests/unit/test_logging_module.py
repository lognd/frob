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
from frob.logging.logger import _under_pytest
from frob.testing import CollectedTests
from frob.tickets import TicketQueue


# frob:ticket T-1621
def test_under_pytest_true_in_this_process():
    # frob:tests \
    # tests/unit/test_logging_module.py::test_under_pytest_true_in_this_process
    # this literally runs inside pytest, so the check must see it
    assert _under_pytest() is True


# frob:ticket T-1621
def test_under_pytest_false_without_pytest_in_sys_modules(monkeypatch):
    # frob:tests src/frob/logging/logger.py::_under_pytest kind="unit"
    from frob.logging import logger as logger_mod

    monkeypatch.setattr(
        logger_mod.sys,
        "modules",
        {k: v for k, v in sys.modules.items() if k != "pytest"},
    )
    assert logger_mod._under_pytest() is False


# frob:ticket T-1621
# frob:tests tests/unit/test_logging_module.py::test_log_record_reported_via_exactly_one_channel_under_pytest  # noqa: E501
def test_log_record_reported_via_exactly_one_channel_under_pytest(capsys, caplog):
    """T-1621: before the fix, ONE `log.warning(...)` call reached pytest's
    report via TWO independent paths -- frob's own `_LazyStderrHandler`
    writing a frob-formatted line to real `sys.stderr` (visible here via
    `capsys`), AND pytest's own logging-capture plugin independently
    recording the same record (visible here via `caplog`) -- making any
    occurrence count taken from the combined output silently 2x. Under
    pytest, frob's own root handlers are now skipped entirely
    (`logger._init`), so the record must reach `caplog` exactly once and
    must NOT also appear in the real captured stdout/stderr text."""
    marker = "COUNT-ONCE-MARKER-T1621"
    log = get_logger("frob.test.count_once_t1621")
    with caplog.at_level(logging.WARNING):
        log.warning(marker)

    matching = [r for r in caplog.records if r.getMessage() == marker]
    assert len(matching) == 1

    captured = capsys.readouterr()
    assert marker not in captured.err
    assert marker not in captured.out


# frob:ticket T-1621
def test_root_logger_has_no_frob_handlers_under_pytest():
    # frob:tests src/frob/logging/logger.py::_init kind="unit"
    from frob.logging.handler import _LazyStderrHandler, _LazyStdoutHandler
    from frob.logging.logger import _init

    _init()  # no-op if already initialized this process -- same real state
    root = logging.getLogger()
    # pytest installs its OWN handlers on root (unrelated to frob); only
    # frob's own stdout/stderr handlers must be absent here.
    assert not any(
        isinstance(h, (_LazyStdoutHandler, _LazyStderrHandler)) for h in root.handlers
    )


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
        v for v in violations if v.rule == "COV001" and "Handler.stream" in v.message
    ]
    assert stream_cov001 == []
