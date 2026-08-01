"""T-1369: `frob ticket land --allow-cross-ticket` must actually reach
`land()`'s `allow_cross_ticket` parameter.

The library-level escape hatch shipped with T-1355 but had no CLI flag, so
a legitimate joint landing (a series worktree hosting several tickets on
one branch, or an open epic whose umbrella scope covers its own leaf's
files) was unlandable with no override at all. These tests pin the whole
path -- parser -> AppConfig -> `land()` keyword -- rather than any single
link, because every previous break in this chain was a wiring gap, not a
logic bug.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from frob._cli_parsers._ticket import _add_ticket_land_parser
from frob.app.config import AppConfig


def _parse(argv: list[str]) -> argparse.Namespace:
    """Parse `argv` through the real top-level parser the CLI builds."""
    parser = argparse.ArgumentParser(prog="frob")
    sub = parser.add_subparsers(dest="ticket_cmd")
    _add_ticket_land_parser(sub)
    return parser.parse_args(argv)


class TestAllowCrossTicketFlagParsing:
    # frob:tests src/frob/_cli_parsers/_ticket.py::_add_ticket_land_parser kind="unit"
    # frob:ticket T-1369
    def test_flag_sets_the_namespace_dest(self) -> None:
        """`--allow-cross-ticket` lands on the dest AppConfig reads."""
        args = _parse(
            ["land", "T-0001", "--worktree", "/tmp/wt", "--allow-cross-ticket"]
        )
        assert args.ticket_allow_cross_ticket is True

    # frob:ticket T-1369
    def test_absent_flag_defaults_false(self) -> None:
        """Omitting it must NOT silently enable the escape hatch."""
        args = _parse(["land", "T-0001", "--worktree", "/tmp/wt"])
        assert args.ticket_allow_cross_ticket is False


class TestAllowCrossTicketReachesConfig:
    # frob:tests src/frob/app/config.py::AppConfig kind="unit"
    # frob:ticket T-1369
    def test_from_external_carries_the_flag(self, tmp_path: Path) -> None:
        """T-1369's real failure mode: a parser dest that `from_external`
        never copies onto AppConfig reads as False forever."""
        args = _parse(
            ["land", "T-0001", "--worktree", "/tmp/wt", "--allow-cross-ticket"]
        )
        cfg = AppConfig.from_external(args, tmp_path / "frob.toml")
        assert cfg.ticket_allow_cross_ticket is True

    # frob:ticket T-1369
    def test_from_external_default_is_false(self, tmp_path: Path) -> None:
        args = _parse(["land", "T-0001", "--worktree", "/tmp/wt"])
        cfg = AppConfig.from_external(args, tmp_path / "frob.toml")
        assert cfg.ticket_allow_cross_ticket is False


class TestAllowCrossTicketReachesLand:
    """The end of the chain: `_land_cmd` must pass the config value into
    `land()` as `allow_cross_ticket`."""

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land kind="unit"
    # frob:ticket T-1369
    @pytest.mark.parametrize("enabled", [True, False])
    def test_land_receives_the_keyword(
        self, monkeypatch, tmp_path: Path, enabled: bool
    ) -> None:
        """Both states are pinned: a flag that is always-True is as broken
        as one that is always-False."""
        from frob.app.ticket_runner import _land_cmd

        seen: dict[str, object] = {}

        def _fake_land(*args: object, **kwargs: object):
            seen.update(kwargs)
            raise _StopLand

        import frob.tickets as _tickets

        # `_land` does `from frob.tickets import land` at call time, so the
        # patch must target the SOURCE module, not `_land_cmd`'s namespace.
        monkeypatch.setattr(_tickets, "land", _fake_land)
        monkeypatch.setattr(_land_cmd, "_absorb_pre_land_fixes", lambda *a, **k: None)
        monkeypatch.setattr(_land_cmd, "_resolve_land_root", lambda root, *a, **k: root)

        argv = ["land", "T-0001", "--worktree", str(tmp_path)]
        if enabled:
            argv.append("--allow-cross-ticket")
        cfg = AppConfig.from_external(_parse(argv), tmp_path / "frob.toml")

        with pytest.raises(_StopLand):
            _land_cmd._land(tmp_path, cfg)

        assert seen["allow_cross_ticket"] is enabled


class _StopLand(Exception):
    """Sentinel: stop `run_land` the moment `land()` is reached, so the
    test asserts on the call's arguments without running a real land."""
