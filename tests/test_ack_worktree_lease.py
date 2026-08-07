"""T-0507: the worktree-lease guard extended to `frob ack` (the T-0431
pattern applied to `frob.app.ack_runner.run`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.ack_runner import run
from frob.app.config import AppConfig
from frob.tickets._worktree_guard import FROB_WORKTREE_ENV


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "x.txt").write_text("x\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


class TestAckWorktreeLease:
    def test_mismatched_lease_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_ack_worktree_lease.py::TestAckWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path / "elsewhere"))
        cfg = AppConfig(ack_refs=["some.ref"], ack_path=tmp_path)
        with pytest.raises(SystemExit):
            run(cfg)
        # the guard refuses before ever touching frob.lock
        assert not (tmp_path / "frob.lock").exists()

    def test_no_lease_reaches_normal_ack_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog
    ) -> None:
        # frob:tests tests/test_ack_worktree_lease.py::TestAckWorktreeLease.test_no_lease_reaches_normal_ack_failure  # noqa: E501
        """With no lease set, the guard is a no-op -- the call proceeds to
        its ordinary logic (here, failing for the mundane reason that
        'some.ref' does not resolve in the graph, NOT the lease guard)."""
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        _init_repo(tmp_path)
        cfg = AppConfig(
            ack_refs=["some.ref.that.does.not.exist"],
            ack_path=tmp_path,
            # T-1317: a real reason so the call reaches acknowledge()'s own
            # unresolved-ref failure rather than the reason-missing gate.
            ack_reason="re-verified against the current source, still accurate",
        )
        with pytest.raises(SystemExit):
            run(cfg)
        assert "worktree lease violation" not in caplog.text
