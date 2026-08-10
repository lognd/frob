"""T-1556: `_emit_scope_closure_warnings` -- a mega-glob scope's scope-
closure feedback used to log one WARNING per gap unconditionally, up to
thousands of lines for a broad scope, burying the first few (usually the
most actionable) hints. This collapses anything past a small threshold
into a single counted-summary line, with `FROB_SCOPE_CLOSURE_VERBOSE=1`
as the escape hatch back to full output."""

from __future__ import annotations

import logging

import pytest

from frob.app.ticket_runner._new import (
    _SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD,
    _emit_scope_closure_warnings,
)


class TestEmitScopeClosureWarnings:
    def test_no_warnings_logs_nothing(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING):
            _emit_scope_closure_warnings("ticket new", "T-0001", ())
        assert caplog.records == []

    def test_few_warnings_logged_individually(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        warnings = tuple(f"gap {i}" for i in range(3))
        with caplog.at_level(logging.WARNING):
            _emit_scope_closure_warnings("ticket new", "T-0001", warnings)
        messages = [r.message for r in caplog.records]
        assert len(messages) == 3
        for i in range(3):
            assert any(f"gap {i}" in m for m in messages)
        # No collapse summary line for a small set.
        assert not any("collapsed" in m for m in messages)

    def test_many_warnings_collapse_to_counted_summary(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("FROB_SCOPE_CLOSURE_VERBOSE", raising=False)
        total = _SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD + 20
        warnings = tuple(f"gap {i}" for i in range(total))
        with caplog.at_level(logging.WARNING):
            _emit_scope_closure_warnings("ticket new", "T-0001", warnings)
        messages = [r.message for r in caplog.records]
        # Threshold individual lines, plus exactly one summary line --
        # signal (the first N gaps) is never drowned by the rest.
        assert len(messages) == _SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD + 1
        summary = messages[-1]
        assert "20 more warning(s) collapsed" in summary
        assert "FROB_SCOPE_CLOSURE_VERBOSE=1" in summary
        assert str(total) in summary

    def test_verbose_env_var_disables_collapse(
        self, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("FROB_SCOPE_CLOSURE_VERBOSE", "1")
        total = _SCOPE_CLOSURE_WARNING_COLLAPSE_THRESHOLD + 20
        warnings = tuple(f"gap {i}" for i in range(total))
        with caplog.at_level(logging.WARNING):
            _emit_scope_closure_warnings("ticket new", "T-0001", warnings)
        messages = [r.message for r in caplog.records]
        assert len(messages) == total
        assert not any("collapsed" in m for m in messages)
