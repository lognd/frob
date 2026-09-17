"""Unit tests for T-3613's default-agent-path switch
(`frob.app.ticket_runner._land_cmd._apply_land_default_queue`) and the
`--status` completion-record poll (`_land_status_cmd`) -- no git/subprocess
plumbing needed, so these stay plain `AppConfig`/`tmp_path`-level tests
rather than the full `tests/ticket_land_suite/` fixture-repo harness."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._land_cmd import (
    _apply_land_default_queue,
    _land_status_cmd,
)
from frob.tickets._land_queue import enqueue


class TestApplyLandDefaultQueue:
    """T-3613 acceptance[1]: a bare `frob ticket land <id>` call under
    `FROB_AGENT` (or `land_default="queue"`) is promoted to `--queue`
    instead of landing synchronously -- but never when an explicit mode
    flag or `--dry-run` is already present."""

    def _base_cfg(self, tmp_path: Path, **overrides: object) -> AppConfig:
        defaults: dict[str, Any] = {
            "ticket_id": "T-0001",
            "ticket_worktree": tmp_path / "wt",
        }
        defaults.update(overrides)
        return AppConfig.model_validate(defaults)

    def test_frob_agent_env_promotes_to_queue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue kind="unit"  # noqa: E501
        monkeypatch.setenv("FROB_AGENT", "1")
        cfg = self._base_cfg(tmp_path)
        result = _apply_land_default_queue(cfg)
        assert result.ticket_land_queue is True

    def test_land_default_config_promotes_to_queue(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue kind="unit"  # noqa: E501
        monkeypatch.delenv("FROB_AGENT", raising=False)
        cfg = self._base_cfg(tmp_path, ticket_land_default="queue")
        result = _apply_land_default_queue(cfg)
        assert result.ticket_land_queue is True

    def test_neither_signal_keeps_synchronous_default(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue kind="unit"  # noqa: E501
        monkeypatch.delenv("FROB_AGENT", raising=False)
        cfg = self._base_cfg(tmp_path)
        result = _apply_land_default_queue(cfg)
        assert result.ticket_land_queue is False
        assert result is cfg

    def test_explicit_flag_wins_over_agent_env(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue kind="unit"  # noqa: E501
        # An explicit --drain (needs neither id nor worktree) must never be
        # redirected into an enqueue just because FROB_AGENT is set.
        monkeypatch.setenv("FROB_AGENT", "1")
        cfg = AppConfig(ticket_land_drain=True)
        result = _apply_land_default_queue(cfg)
        assert result is cfg
        assert result.ticket_land_queue is False

    def test_status_flag_is_never_redirected(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue kind="unit"  # noqa: E501
        monkeypatch.setenv("FROB_AGENT", "1")
        cfg = AppConfig(ticket_land_status="T-0001")
        result = _apply_land_default_queue(cfg)
        assert result is cfg
        assert result.ticket_land_queue is False

    def test_dry_run_is_never_promoted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue kind="unit"  # noqa: E501
        monkeypatch.setenv("FROB_AGENT", "1")
        cfg = self._base_cfg(tmp_path, ticket_dry_run=True)
        result = _apply_land_default_queue(cfg)
        assert result is cfg
        assert result.ticket_land_queue is False

    def test_missing_id_or_worktree_is_never_promoted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_apply_land_default_queue kind="unit"  # noqa: E501
        monkeypatch.setenv("FROB_AGENT", "1")
        cfg = AppConfig(ticket_id=None, ticket_worktree=None)
        result = _apply_land_default_queue(cfg)
        assert result is cfg
        assert result.ticket_land_queue is False


class TestLandStatusCmd:
    """T-3613 acceptance[2]: `frob ticket land --status <id>` prints the
    per-intent completion record and exits nonzero when there is none."""

    def test_status_prints_queued_record(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_status_cmd kind="unit"  # noqa: E501
        enqueue(tmp_path, "T-0001", tmp_path / "wt", "b1")
        cfg = AppConfig(ticket_land_status="T-0001")
        _land_status_cmd(tmp_path, cfg)
        printed = json.loads(capsys.readouterr().out)
        assert printed["ticket_id"] == "T-0001"
        assert printed["status"] == "queued"

    def test_status_missing_record_exits_nonzero(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_status_cmd kind="unit"  # noqa: E501
        cfg = AppConfig(ticket_land_status="T-9999")
        with pytest.raises(SystemExit) as exc_info:
            _land_status_cmd(tmp_path, cfg)
        assert exc_info.value.code == 1
