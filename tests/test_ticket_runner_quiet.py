"""`frob ticket` default-quiet dispatch (T-0768): diagnostic loggers are
clamped to WARNING during subcommand dispatch while the runner's own
output logger stays at INFO; `-v` skips the clamp entirely."""

from __future__ import annotations

import contextlib
import logging

from frob.app.config import AppConfig
from frob.app.ticket_runner import _diagnostic_log_ctx


class TestDiagnosticLogCtx:
    """T-0768: `_diagnostic_log_ctx` gates the clamp on `ticket_verbose`."""

    def test_default_clamps_frob_tree_but_pins_runner_output(self) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_diagnostic_log_ctx \
        # kind="unit"
        cfg = AppConfig(ticket_command="list", ticket_verbose=0)
        frob_logger = logging.getLogger("frob")
        runner_logger = logging.getLogger("frob.app.ticket_runner")
        gitio_logger = logging.getLogger("frob.gitio")
        before_frob = frob_logger.level
        before_runner = runner_logger.level
        with _diagnostic_log_ctx(cfg):
            assert frob_logger.level == logging.WARNING
            assert runner_logger.getEffectiveLevel() == logging.INFO
            # The diagnostic chatter sources inherit the WARNING clamp.
            assert gitio_logger.getEffectiveLevel() == logging.WARNING
        assert frob_logger.level == before_frob
        assert runner_logger.level == before_runner

    def test_verbose_skips_the_clamp(self) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_diagnostic_log_ctx \
        # kind="unit"
        cfg = AppConfig(ticket_command="list", ticket_verbose=1)
        ctx = _diagnostic_log_ctx(cfg)
        assert isinstance(ctx, contextlib.nullcontext)
        frob_logger = logging.getLogger("frob")
        before = frob_logger.level
        with ctx:
            assert frob_logger.level == before

    # frob:ticket T-3000
    def test_global_frob_verbose_env_var_also_skips_the_clamp(
        self, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_diagnostic_log_ctx \
        # kind="unit"
        """T-3000: the GLOBAL `-v`/`--verbose` flag (`frob -v ticket show
        T-1`) sets `FROB_VERBOSE=1` via `_apply_verbose_env_override`
        before dispatch -- `ticket_verbose` stays 0 in this case (that
        field is populated only by `ticket`'s OWN local `-v`, placed
        between `ticket` and its leaf subcommand). Before the fix, this
        clamp checked ONLY `ticket_verbose`, so the global flag was
        silently accepted (no argparse error) but had no effect: `frob
        -v ticket show T-1` printed the same WARNING-clamped output as
        no `-v` at all, while `frob ticket -v show T-1` worked."""
        monkeypatch.setenv("FROB_VERBOSE", "1")
        cfg = AppConfig(ticket_command="list", ticket_verbose=0)
        ctx = _diagnostic_log_ctx(cfg)
        assert isinstance(ctx, contextlib.nullcontext)
        frob_logger = logging.getLogger("frob")
        before = frob_logger.level
        with ctx:
            assert frob_logger.level == before

    # frob:ticket T-3000
    def test_global_frob_log_level_env_var_also_skips_the_clamp(
        self, monkeypatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_diagnostic_log_ctx \
        # kind="unit"
        """T-3000: `FROB_LOG_LEVEL=<name>` is the other documented escape
        hatch (`frob.logging.logger._resolve_stdout_level_override`,
        `quiet_query_stdout`) -- must also skip the ticket-local clamp,
        not just `FROB_VERBOSE=1`."""
        monkeypatch.setenv("FROB_LOG_LEVEL", "INFO")
        cfg = AppConfig(ticket_command="list", ticket_verbose=0)
        ctx = _diagnostic_log_ctx(cfg)
        assert isinstance(ctx, contextlib.nullcontext)

    def test_no_verbose_signal_at_all_still_clamps(self, monkeypatch) -> None:
        # frob:tests src/frob/app/ticket_runner/__init__.py::_diagnostic_log_ctx \
        # kind="unit"
        """T-3000 must-stay-quiet twin: with neither `ticket_verbose` nor
        either env var set, the clamp still applies -- the fix must not
        widen this into an always-on nullcontext."""
        monkeypatch.delenv("FROB_VERBOSE", raising=False)
        monkeypatch.delenv("FROB_LOG_LEVEL", raising=False)
        cfg = AppConfig(ticket_command="list", ticket_verbose=0)
        ctx = _diagnostic_log_ctx(cfg)
        assert not isinstance(ctx, contextlib.nullcontext)
