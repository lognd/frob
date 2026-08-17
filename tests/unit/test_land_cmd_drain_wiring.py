"""Unit tests for `frob.app.ticket_runner._land_cmd._land_core_finish_
post_land`'s T-2317 wiring: the rapid-land branch fires `frob.verify.
_drain.spawn_deferred_drain` alongside the existing `spawn_deferred_
post_land_sweep` call, both deferred-imported inside the function body --
so, matching this module's own established pattern (see
`test_land_cmd_backpressure.py`'s docstring), every test here monkeypatches
the two spawn functions on their OWN defining modules
(`frob.app.ticket_runner._rapid_sweep`, `frob.verify._drain`), never on
`_land_cmd`'s namespace, since the deferred `from ... import ...` inside
the function body re-reads those modules' attributes at CALL time."""

from __future__ import annotations

from pathlib import Path

import pytest

import frob.app.ticket_runner._rapid_sweep as rapid_sweep_mod
import frob.verify._drain as drain_mod
from frob.app.config import AppConfig
from frob.app.ticket_runner._land_cmd import _land_core_finish_post_land
from frob.tickets._models import LandReport


def _make_report(*, dry_run: bool = False, commit_sha: str | None = "deadbeef") -> LandReport:
    return LandReport(
        ticket_id="T-9000",
        final_id="T-9000",
        dry_run=dry_run,
        wip_committed=True,
        merged_main_into_worktree=True,
        ledger_spliced=True,
        commit_sha=commit_sha,
    )


class TestRapidLandDrainWiring:
    """T-2317: the rapid-land branch of `_land_core_finish_post_land`
    fires `spawn_deferred_drain` immediately after `spawn_deferred_post_
    land_sweep`, under the SAME guard (`not dry_run and commit_sha is not
    None`) -- never on its own looser or stricter condition."""

    # frob:ticket T-2317
    def test_real_rapid_land_spawns_both_sweep_and_drain(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring.test_real_rapid_land_spawns_both_sweep_and_drain  # noqa: E501
        calls: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod,
            "spawn_deferred_post_land_sweep",
            lambda root, ticket_id, final_id, commit_sha: calls.append("sweep"),
        )
        monkeypatch.setattr(
            drain_mod,
            "spawn_deferred_drain",
            lambda root, ticket_id: calls.append("drain"),
        )
        cfg = AppConfig(ticket_id="T-9000")
        report = _make_report()

        result = _land_core_finish_post_land(
            tmp_path, cfg, report, None, None, rapid_land=True
        )

        assert result.is_ok
        assert calls == ["sweep", "drain"]

    # frob:ticket T-2317
    def test_dry_run_spawns_neither(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring.test_dry_run_spawns_neither  # noqa: E501
        calls: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod,
            "spawn_deferred_post_land_sweep",
            lambda *a, **k: calls.append("sweep"),
        )
        monkeypatch.setattr(
            drain_mod, "spawn_deferred_drain", lambda *a, **k: calls.append("drain")
        )
        cfg = AppConfig(ticket_id="T-9000")
        report = _make_report(dry_run=True)

        result = _land_core_finish_post_land(
            tmp_path, cfg, report, None, None, rapid_land=True
        )

        assert result.is_ok
        assert calls == []

    # frob:ticket T-2317
    def test_no_commit_sha_spawns_neither(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_drain_wiring.py::TestRapidLandDrainWiring.test_no_commit_sha_spawns_neither  # noqa: E501
        calls: list[str] = []
        monkeypatch.setattr(
            rapid_sweep_mod,
            "spawn_deferred_post_land_sweep",
            lambda *a, **k: calls.append("sweep"),
        )
        monkeypatch.setattr(
            drain_mod, "spawn_deferred_drain", lambda *a, **k: calls.append("drain")
        )
        cfg = AppConfig(ticket_id="T-9000")
        report = _make_report(commit_sha=None)

        result = _land_core_finish_post_land(
            tmp_path, cfg, report, None, None, rapid_land=True
        )

        assert result.is_ok
        assert calls == []
