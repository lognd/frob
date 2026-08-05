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
    # frob:tests src/frob/_cli_parsers/_ticket/_progress.py::_add_ticket_land_parser \
    # kind="unit"
    # frob:ticket T-1369
    # frob:ticket T-1424
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


# frob:ticket T-1444
class TestQueueDrainFlagParsing:
    # frob:tests src/frob/_cli_parsers/_ticket/_progress.py::_add_ticket_land_parser \
    # kind="unit"
    def test_queue_flag_sets_the_namespace_dest(self) -> None:
        """`--queue` lands on the dest AppConfig reads."""
        args = _parse(["land", "T-0001", "--worktree", "/tmp/wt", "--queue"])
        assert args.ticket_land_queue is True

    def test_drain_flag_sets_the_namespace_dest(self) -> None:
        """`--drain` lands on the dest AppConfig reads, and needs neither
        <id> nor --worktree (T-1444's own no-longer-required change)."""
        args = _parse(["land", "--drain"])
        assert args.ticket_land_drain is True
        assert args.ticket_id is None
        assert args.ticket_worktree is None

    def test_absent_flags_default_false(self) -> None:
        args = _parse(["land", "T-0001", "--worktree", "/tmp/wt"])
        assert args.ticket_land_queue is False
        assert args.ticket_land_drain is False


# frob:ticket T-1444
class TestQueueDrainReachesConfig:
    # frob:tests src/frob/app/config.py::AppConfig kind="unit"
    def test_from_external_carries_queue(self, tmp_path: Path) -> None:
        """T-1369's own precedent incident (a parser dest AppConfig.
        from_external silently drops) applies here too -- WIRE001 caught
        exactly this gap for --no-cache in the T-1445 sibling ticket."""
        args = _parse(["land", "T-0001", "--worktree", "/tmp/wt", "--queue"])
        cfg = AppConfig.from_external(args, tmp_path / "frob.toml")
        assert cfg.ticket_land_queue is True

    def test_from_external_carries_drain(self, tmp_path: Path) -> None:
        args = _parse(["land", "--drain"])
        cfg = AppConfig.from_external(args, tmp_path / "frob.toml")
        assert cfg.ticket_land_drain is True


# frob:ticket T-1444
class TestLandDispatchesToQueueOrDrain:
    """`_land`'s own dispatch: --queue and --drain must short-circuit
    BEFORE `_require_land_args`/`_land_core` -- a --drain call has no
    <id>/--worktree at all, so falling through to the normal path would
    always refuse."""

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land kind="unit"
    def test_queue_flag_calls_land_enqueue_not_land_core(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        from frob.app.ticket_runner import _land_cmd

        called: list[str] = []
        monkeypatch.setattr(
            _land_cmd, "_land_enqueue", lambda *a, **k: called.append("enqueue")
        )
        monkeypatch.setattr(
            _land_cmd,
            "_land_core",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run")),
        )
        argv = ["land", "T-0001", "--worktree", str(tmp_path), "--queue"]
        cfg = AppConfig.from_external(_parse(argv), tmp_path / "frob.toml")

        _land_cmd._land(tmp_path, cfg)

        assert called == ["enqueue"]

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land kind="unit"
    def test_drain_flag_calls_land_drain_not_require_land_args(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        from frob.app.ticket_runner import _land_cmd

        called: list[str] = []
        monkeypatch.setattr(
            _land_cmd, "_land_drain", lambda *a, **k: called.append("drain")
        )
        monkeypatch.setattr(
            _land_cmd,
            "_require_land_args",
            lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run")),
        )
        argv = ["land", "--drain"]
        cfg = AppConfig.from_external(_parse(argv), tmp_path / "frob.toml")

        _land_cmd._land(tmp_path, cfg)

        assert called == ["drain"]


# frob:ticket T-1444
class TestLandEnqueue:
    """`_land_enqueue` (T-1444): the `--queue` CLI handler -- calls
    `frob.tickets.enqueue` with the worktree's own directory name as the
    branch, and exits 1 on a `QueueError` instead of silently succeeding."""

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_enqueue kind="unit"
    def test_enqueue_success_reaches_land_queue_enqueue(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        from frob.app.ticket_runner import _land_cmd

        seen: dict[str, object] = {}

        def _fake_enqueue(root, ticket_id, worktree, branch):  # noqa: ANN001
            seen.update(
                {
                    "root": root,
                    "ticket_id": ticket_id,
                    "worktree": worktree,
                    "branch": branch,
                }
            )
            from typani.result import Ok

            from frob.tickets import QueueEntry

            return Ok(
                QueueEntry(
                    ticket_id=ticket_id,
                    worktree=str(worktree),
                    branch=branch,
                    enqueued_at="2026-01-01T00:00:00+00:00",
                )
            )

        import frob.tickets as _tickets

        monkeypatch.setattr(_tickets, "enqueue", _fake_enqueue)
        argv = ["land", "T-0001", "--worktree", str(tmp_path), "--queue"]
        cfg = AppConfig.from_external(_parse(argv), tmp_path / "frob.toml")

        _land_cmd._land_enqueue(tmp_path, cfg)

        assert seen["ticket_id"] == "T-0001"
        assert seen["worktree"] == tmp_path

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_enqueue kind="unit"
    def test_enqueue_failure_exits_nonzero(self, monkeypatch, tmp_path: Path) -> None:
        from frob.app.ticket_runner import _land_cmd

        def _fake_enqueue(root, ticket_id, worktree, branch):  # noqa: ANN001
            from typani.result import Err

            from frob.tickets import QueueError

            return Err(QueueError.AlreadyQueued)

        import frob.tickets as _tickets

        monkeypatch.setattr(_tickets, "enqueue", _fake_enqueue)
        argv = ["land", "T-0001", "--worktree", str(tmp_path), "--queue"]
        cfg = AppConfig.from_external(_parse(argv), tmp_path / "frob.toml")

        with pytest.raises(SystemExit) as exc_info:
            _land_cmd._land_enqueue(tmp_path, cfg)
        assert exc_info.value.code == 1


# frob:ticket T-1444
class TestLandDrain:
    """`_land_drain` (T-1444): the `--drain` CLI handler -- loops
    `frob.tickets.drain_next` until it reports no more queued entries,
    calling `_land_core` per entry (not the CLI-only `_land` tail)."""

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_drain kind="unit"
    def test_empty_queue_drains_zero_and_returns(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        from frob.app.ticket_runner import _land_cmd

        def _fake_drain_next(root, land_fn):  # noqa: ANN001
            from typani.result import Ok

            return Ok(None)

        import frob.tickets as _tickets

        monkeypatch.setattr(_tickets, "drain_next", _fake_drain_next)
        argv = ["land", "--drain"]
        cfg = AppConfig.from_external(_parse(argv), tmp_path / "frob.toml")

        # Must not raise/exit -- an empty queue is a normal, successful
        # zero-work drain.
        _land_cmd._land_drain(tmp_path, cfg)

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_land_drain kind="unit"
    def test_two_entries_call_land_core_per_entry_with_its_own_ticket_id(
        self, monkeypatch, tmp_path: Path
    ) -> None:
        """T-1444's own attribution requirement: each queued entry must be
        landed against ITS OWN ticket_id/worktree, not the CLI's (there is
        no single CLI ticket_id for --drain)."""
        from frob.app.ticket_runner import _land_cmd

        entries = [
            {
                "ticket_id": "T-0001",
                "worktree": str(tmp_path / "wt1"),
                "branch": "t-0001",
                "enqueued_at": "2026-01-01T00:00:00+00:00",
                "status": "queued",
            },
            {
                "ticket_id": "T-0002",
                "worktree": str(tmp_path / "wt2"),
                "branch": "t-0002",
                "enqueued_at": "2026-01-01T00:00:01+00:00",
                "status": "queued",
            },
        ]
        land_core_calls: list[str] = []

        def _fake_land_core(root, cfg):  # noqa: ANN001
            from typani.result import Ok

            from frob.tickets._models import LandReport

            land_core_calls.append(cfg.ticket_id)
            return Ok(
                LandReport(
                    ticket_id=cfg.ticket_id,
                    final_id=cfg.ticket_id,
                    dry_run=False,
                    wip_committed=False,
                    merged_main_into_worktree=False,
                    ledger_spliced=False,
                    commit_sha="deadbeef",
                )
            )

        def _fake_drain_next(root, land_fn):  # noqa: ANN001
            from typani.result import Ok

            from frob.tickets import QueueEntry

            if not entries:
                return Ok(None)
            raw = entries.pop(0)
            entry = QueueEntry(**{**raw, "status": "queued"})
            outcome = land_fn(entry)
            landed = entry.model_copy(
                update={
                    "status": "landed" if outcome.is_ok else "failed",
                    "commit_sha": outcome.danger_ok.commit_sha
                    if outcome.is_ok
                    else None,
                }
            )
            return Ok(landed)

        import frob.tickets as _tickets

        monkeypatch.setattr(_tickets, "drain_next", _fake_drain_next)
        monkeypatch.setattr(_land_cmd, "_land_core", _fake_land_core)
        monkeypatch.setattr(_land_cmd, "_print_land_proof", lambda *a, **k: True)
        argv = ["land", "--drain"]
        cfg = AppConfig.from_external(_parse(argv), tmp_path / "frob.toml")

        _land_cmd._land_drain(tmp_path, cfg)

        assert land_core_calls == ["T-0001", "T-0002"]
