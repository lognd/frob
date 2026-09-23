"""T-5123: `frob ticket land`'s own post-land tail must attempt to REAP
(remove + delete branch) its own now-terminal worktree, not just
auto-sync it forever -- the measured incident: 183 worktrees/1437
branches accumulated because neither `sweep_worktrees` nor
`remove_worktree` (`frob.tickets._worktree_sweep`) ever sat on the land
path's own tail, so a worktree nobody explicitly `--finish`ed was never
reaped by anything (T-3797/T-4556, both done for days, still checked
out). `_reap_or_sync_worktree` is a thin dispatcher reusing `remove_
worktree`'s own existing safety gates -- these are isolated unit tests
of that dispatch, not a re-test of `remove_worktree`'s own gates
(already covered by `tests/test_ticket_leases.py::TestRemoveWorktree`).
"""

# frob:ticket T-5123

from __future__ import annotations

from pathlib import Path

import pytest
from typani.result import Ok

from frob.app.ticket_runner import _land_cmd
from frob.tickets import _worktree_sweep
from frob.tickets._worktree_sweep import _WorktreeVerdict


class TestReapOrSyncWorktree:
    """`_reap_or_sync_worktree`'s own dispatch contract: reap when `frob.
    tickets._worktree_sweep.remove_worktree` says it is safe to, else
    fall back to the pre-existing T-1720/T-2173 auto-sync."""

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_reap_or_sync_worktree
    def test_reaps_a_worktree_with_no_further_live_lease(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "root"
        worktree = tmp_path / "wt"
        root.mkdir()
        worktree.mkdir()

        monkeypatch.setattr(
            _worktree_sweep,
            "remove_worktree",
            lambda r, w, **kw: Ok(_WorktreeVerdict(path=str(w), verdict="removed")),
        )
        auto_sync_calls: list[tuple[Path, Path, str]] = []
        monkeypatch.setattr(
            _land_cmd,
            "_auto_sync_worktree_onto_main",
            lambda r, w, tid: auto_sync_calls.append((r, w, tid)),
        )
        branch_delete_calls: list[tuple[Path, str | None, str]] = []
        monkeypatch.setattr(
            _land_cmd,
            "_delete_worktree_branch",
            lambda r, b, tid: branch_delete_calls.append((r, b, tid)),
        )
        monkeypatch.setattr(_land_cmd, "_worktree_branch_name", lambda r, w: "t-0001")

        _land_cmd._reap_or_sync_worktree(root, worktree, "T-0001")

        assert branch_delete_calls == [(root, "t-0001", "T-0001")]
        assert auto_sync_calls == []

    # frob:tests src/frob/app/ticket_runner/_land_cmd.py::_reap_or_sync_worktree
    def test_falls_back_to_auto_sync_when_still_in_use(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        root = tmp_path / "root"
        worktree = tmp_path / "wt"
        root.mkdir()
        worktree.mkdir()

        monkeypatch.setattr(
            _worktree_sweep,
            "remove_worktree",
            lambda r, w, **kw: Ok(
                _WorktreeVerdict(path=str(w), verdict="kept:lease", detail="T-0002 12s")
            ),
        )
        auto_sync_calls: list[tuple[Path, Path, str]] = []
        monkeypatch.setattr(
            _land_cmd,
            "_auto_sync_worktree_onto_main",
            lambda r, w, tid: auto_sync_calls.append((r, w, tid)),
        )
        branch_delete_calls: list[tuple[Path, str | None, str]] = []
        monkeypatch.setattr(
            _land_cmd,
            "_delete_worktree_branch",
            lambda r, b, tid: branch_delete_calls.append((r, b, tid)),
        )
        monkeypatch.setattr(_land_cmd, "_worktree_branch_name", lambda r, w: "t-0001")

        _land_cmd._reap_or_sync_worktree(root, worktree, "T-0001")

        assert auto_sync_calls == [(root, worktree, "T-0001")]
        assert branch_delete_calls == []
