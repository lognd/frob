"""Direct-call CLI coverage for T-1738's `frob ticket wave --agents N`:
group/remainder plain-text render and `--json` shape, same `AppConfig` +
`ticket_runner.run` direct-call shape as `test_app_runners_t0715_sprint_
tier.py` (T-0160 rationale: CLI-subprocess tests don't attribute coverage
back to the running process)."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run


def _new(tmp_path: Path, *, scope: list[str] | None = None) -> None:
    """File one queued ticket via the real `ticket new` verb, matching
    the existing t0715 test file's direct-call pattern."""
    ticket_run(
        AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="a ticket",
            ticket_kind="feature",
            ticket_scope=scope or [],
        )
    )


class TestWaveCommand:
    """`frob ticket wave --agents N [--json]` (T-1738)."""

    def test_json_render_shape(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand.test_json_render_shape  # noqa: E501
        _new(tmp_path, scope=["src/a.py"])
        _new(tmp_path, scope=["src/b.py"])
        import io
        import logging as _logging

        stream = io.StringIO()
        handler = _logging.StreamHandler(stream)
        logger = _logging.getLogger("frob.app.ticket_runner")
        logger.addHandler(handler)
        logger.setLevel(_logging.INFO)
        try:
            ticket_run(
                AppConfig(
                    ticket_command="wave",
                    ticket_path=tmp_path,
                    ticket_wave_agents=2,
                    ticket_json=True,
                )
            )
        finally:
            logger.removeHandler(handler)
        payload = json.loads(stream.getvalue())
        assert "groups" in payload
        assert "remainder" in payload
        assert len(payload["groups"]) == 2
        assert payload["remainder"] == []

    def test_plain_render_lists_groups_and_remainder(
        self, tmp_path: Path, caplog
    ) -> None:
        # frob:tests tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand.test_plain_render_lists_groups_and_remainder  # noqa: E501
        _new(tmp_path, scope=["src/a.py"])
        _new(tmp_path, scope=["src/b.py"])
        _new(tmp_path, scope=["src/a.py", "src/b.py"])
        with caplog.at_level(logging.INFO, logger="frob.app.ticket_runner"):
            ticket_run(
                AppConfig(
                    ticket_command="wave",
                    ticket_path=tmp_path,
                    ticket_wave_agents=2,
                )
            )
        messages = [r.getMessage() for r in caplog.records]
        assert any("Group 0" in m for m in messages)
        assert any("Group 1" in m for m in messages)
        assert any("Remainder" in m for m in messages)
        assert any("T-0003" in m for m in messages)

    def test_missing_agents_flag_is_a_clean_error(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_app_runners_t1738_wave.py::TestWaveCommand.test_missing_agents_flag_is_a_clean_error  # noqa: E501
        import pytest

        with pytest.raises(SystemExit):
            ticket_run(
                AppConfig(
                    ticket_command="wave",
                    ticket_path=tmp_path,
                )
            )
