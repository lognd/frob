"""CLI tests for `frob pool snapshot|clear` (T-0569)
(docs/modules/gates.md#ratchet-pools)."""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.app import pool_runner
from frob.app.config import AppConfig
from frob.gates._ratchet import load_ratchet_lock


# frob:ticket T-0569
class TestPoolSnapshotCli:
    def test_snapshot_baselines_keys(self, tmp_path: Path) -> None:
        # frob:tests tests/test_pool_runner.py::TestPoolSnapshotCli.test_snapshot_baselines_keys  # noqa: E501
        cfg = AppConfig(
            pool_command="snapshot",
            pool_rule="DEAD001",
            pool_keys=["a.py:1", "b.py:2"],
            pool_path=tmp_path,
        )
        pool_runner.run(cfg)
        lock = load_ratchet_lock(tmp_path)
        pool = lock.pool_for("DEAD001")
        assert pool is not None and pool.keys == {"a.py:1", "b.py:2"}

    # frob:ticket T-0569
    def test_snapshot_requires_rule_and_keys(self, tmp_path: Path) -> None:
        cfg = AppConfig(pool_command="snapshot", pool_path=tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            pool_runner.run(cfg)
        assert exc_info.value.code == 1


# frob:ticket T-0569
class TestPoolClearCli:
    def test_clear_removes_entry_with_reason(self, tmp_path: Path) -> None:
        # frob:tests tests/test_pool_runner.py::TestPoolClearCli.test_clear_removes_entry_with_reason  # noqa: E501
        AppConfig(
            pool_command="snapshot",
            pool_rule="DEAD001",
            pool_keys=["a.py:1"],
            pool_path=tmp_path,
        )
        pool_runner.run(
            AppConfig(
                pool_command="snapshot",
                pool_rule="DEAD001",
                pool_keys=["a.py:1"],
                pool_path=tmp_path,
            )
        )
        pool_runner.run(
            AppConfig(
                pool_command="clear",
                pool_rule="DEAD001",
                pool_key="a.py:1",
                pool_reason="fixed the finding",
                pool_path=tmp_path,
            )
        )
        lock = load_ratchet_lock(tmp_path)
        pool = lock.pool_for("DEAD001")
        assert pool is not None and "a.py:1" not in pool.keys

    # frob:ticket T-0569
    def test_clear_requires_reason(self, tmp_path: Path) -> None:
        pool_runner.run(
            AppConfig(
                pool_command="snapshot",
                pool_rule="DEAD001",
                pool_keys=["a.py:1"],
                pool_path=tmp_path,
            )
        )
        cfg = AppConfig(
            pool_command="clear",
            pool_rule="DEAD001",
            pool_key="a.py:1",
            pool_path=tmp_path,
        )
        with pytest.raises(SystemExit) as exc_info:
            pool_runner.run(cfg)
        assert exc_info.value.code == 1


# frob:ticket T-0569
class TestPoolRunDispatch:
    def test_unknown_command_exits_nonzero(self, tmp_path: Path) -> None:
        cfg = AppConfig(pool_command=None, pool_path=tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            pool_runner.run(cfg)
        assert exc_info.value.code == 1
