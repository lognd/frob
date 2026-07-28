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
        # frob:tests src/frob/app/ticket_runner/__init__.py::_diagnostic_log_ctx kind="unit"
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
        # frob:tests src/frob/app/ticket_runner/__init__.py::_diagnostic_log_ctx kind="unit"
        cfg = AppConfig(ticket_command="list", ticket_verbose=1)
        ctx = _diagnostic_log_ctx(cfg)
        assert isinstance(ctx, contextlib.nullcontext)
        frob_logger = logging.getLogger("frob")
        before = frob_logger.level
        with ctx:
            assert frob_logger.level == before
