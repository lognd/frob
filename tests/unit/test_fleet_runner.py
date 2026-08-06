"""Unit tests for `frob.app.fleet_runner` (T-0573 CLI wiring): `status`
table/JSON output and `route`'s manifest-error/success dispatch. `frob.fleet`
internals are exercised directly in tests/unit/fleet/; this file is purely
about the CLI dispatch layer around them."""


from __future__ import annotations

from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.fleet_runner import run
from frob.fleet import FleetReport, GateSummary, RepoStatus


class TestFleetRunner:
    def test_run_status_table(self, tmp_path: Path, monkeypatch, capsys) -> None:
        manifest_path = tmp_path / "fleet.toml"
        manifest_path.write_text('[[repo]]\nname = "a"\npath = "."\n')

        monkeypatch.setattr(
            "frob.app.fleet_runner.rollup",
            lambda manifest, probe_gates=True: FleetReport(  # noqa: ARG005
                repos=(
                    RepoStatus(
                        name="a",
                        path=Path("."),
                        branch="main",
                        dirty=False,
                        gates=GateSummary(),
                        doable_count=1,
                    ),
                )
            ),
        )
        cfg = AppConfig(fleet_manifest=manifest_path)
        run(cfg)
        out = capsys.readouterr().out
        assert "repo" in out
        assert "a" in out
        assert "main" in out

    def test_run_status_missing_manifest(self, tmp_path: Path) -> None:
        cfg = AppConfig(fleet_manifest=tmp_path / "nope.toml")
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code == 1

    def test_run_route_ok(self, tmp_path: Path, monkeypatch, capsys) -> None:
        manifest_path = tmp_path / "fleet.toml"
        manifest_path.write_text('[[repo]]\nname = "a"\npath = "."\n')

        from typani.result import Ok

        monkeypatch.setattr(
            "frob.app.fleet_runner.route_ticket",
            lambda manifest, repo, spec: Ok("T-9999"),  # noqa: ARG005
        )
        cfg = AppConfig(
            fleet_command="route",
            fleet_manifest=manifest_path,
            fleet_repo="a",
            fleet_title="test",
        )
        run(cfg)
        out = capsys.readouterr().out
        assert "T-9999" in out
        assert "a" in out

    def test_run_route_missing_flags(self, tmp_path: Path) -> None:
        manifest_path = tmp_path / "fleet.toml"
        manifest_path.write_text('[[repo]]\nname = "a"\npath = "."\n')
        cfg = AppConfig(fleet_command="route", fleet_manifest=manifest_path)
        with pytest.raises(SystemExit) as exc_info:
            run(cfg)
        assert exc_info.value.code == 1
