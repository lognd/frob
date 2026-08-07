"""Unit tests for `frob.app.ticket_runner._land_cmd._apply_backpressure`
(T-1692): the land-path wiring of `frob.verify`'s depth/age ceilings.

`_apply_backpressure` deferred-imports `ceilings_for_profile`/
`block_until_watermark_advances` from `frob.verify` INSIDE its own body
(matching this module's existing deferred-import convention for
`frob.verify`/`frob.graph`), so every test here monkeypatches those two
names directly on the `frob.verify` module object -- patching
`_land_cmd`'s own module namespace would have no effect, since the
`from frob.verify import ...` statement re-reads `frob.verify`'s
attributes at CALL time, not at `_land_cmd` import time."""

from __future__ import annotations

from pathlib import Path

import pytest
from typani.result import Err, Ok

import frob.verify as verify_mod
from frob.app.config import AppConfig
from frob.app.ticket_runner._land_cmd import _apply_backpressure
from frob.tickets._profile import ProfileName
from frob.verify import BackpressureCeilings, BackpressureError


class TestApplyBackpressure:
    """`_apply_backpressure` skips under `--dry-run`, is a no-op when the
    queue is under ceiling, and blocks (via `frob.verify.
    block_until_watermark_advances`) when it is not."""

    def test_dry_run_skips_the_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_dry_run_skips_the_check  # noqa: E501
        calls: list[str] = []
        monkeypatch.setattr(
            verify_mod, "ceilings_for_profile", lambda profile, root: calls.append("c")
        )
        monkeypatch.setattr(
            verify_mod,
            "block_until_watermark_advances",
            lambda root, ceilings, ticket_id, **kw: calls.append("b"),
        )
        cfg = AppConfig(ticket_id="T-9000", ticket_dry_run=True)
        _apply_backpressure(tmp_path, cfg, ProfileName.STANDARD)
        # Neither the ceiling lookup nor the block call is ever reached --
        # the dry-run guard returns before the deferred import runs.
        assert calls == []

    def test_not_tripped_is_a_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_not_tripped_is_a_noop  # noqa: E501
        calls: list[str] = []
        monkeypatch.setattr(
            verify_mod,
            "ceilings_for_profile",
            lambda profile, root: BackpressureCeilings(max_depth=5, max_age_s=None),
        )
        monkeypatch.setattr(
            verify_mod,
            "block_until_watermark_advances",
            lambda root, ceilings, ticket_id, **kw: calls.append(ticket_id) or Ok(None),
        )
        cfg = AppConfig(ticket_id="T-9000", ticket_dry_run=False)
        _apply_backpressure(tmp_path, cfg, ProfileName.STANDARD)
        # block_until_watermark_advances is ALWAYS called (it is the one
        # place that knows whether the ceiling is tripped) -- this test
        # asserts the not-tripped case flows straight through without
        # error, not that the call is skipped.
        assert calls == ["T-9000"]

    def test_tripped_blocks_then_proceeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_tripped_blocks_then_proceeds  # noqa: E501
        calls: list[tuple] = []
        monkeypatch.setattr(
            verify_mod,
            "ceilings_for_profile",
            lambda profile, root: BackpressureCeilings(max_depth=0, max_age_s=0.0),
        )

        def _fake_block(root, ceilings, ticket_id, **kw):  # noqa: ANN001
            calls.append((root, ceilings, ticket_id))
            return Ok(None)

        monkeypatch.setattr(verify_mod, "block_until_watermark_advances", _fake_block)
        cfg = AppConfig(ticket_id="T-9000", ticket_dry_run=False)
        _apply_backpressure(tmp_path, cfg, ProfileName.STANDARD)
        assert len(calls) == 1
        assert calls[0][2] == "T-9000"
        assert calls[0][1].max_depth == 0

    def test_block_timeout_logs_and_proceeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_land_cmd_backpressure.py::TestApplyBackpressure.test_block_timeout_logs_and_proceeds  # noqa: E501
        monkeypatch.setattr(
            verify_mod,
            "ceilings_for_profile",
            lambda profile, root: BackpressureCeilings(max_depth=0, max_age_s=0.0),
        )
        monkeypatch.setattr(
            verify_mod,
            "block_until_watermark_advances",
            lambda root, ceilings, ticket_id, **kw: Err(BackpressureError.BlockTimedOut),
        )
        cfg = AppConfig(ticket_id="T-9000", ticket_dry_run=False)
        # Must not raise -- a timed-out block logs at ERROR and the land
        # proceeds anyway (see `_apply_backpressure`'s own docstring).
        _apply_backpressure(tmp_path, cfg, ProfileName.STANDARD)
