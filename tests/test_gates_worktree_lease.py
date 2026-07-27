"""T-0431: the worktree-lease guard wired into the gate-state stamping
commands (`frob check --stamp-baseline`/`--stamp-coverage`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.gates import stamp_baseline, stamp_coverage
from frob.gates._models import GateError
from frob.tickets._worktree_guard import FROB_WORKTREE_ENV


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:waive DUP001 reason="parallel per-domain test scaffolding across \
# test_ack_worktree_lease.py, test_gates_worktree_lease.py, \
# test_release_worktree_lease.py (3 sites) -- each file exercises a \
# structurally similar check for a distinct domain/module with the \
# same arrange-act shape; extracting would blur which domain owns \
# which check"
def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "x.txt").write_text("x\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


class TestStampBaselineWorktreeLease:
    def test_mismatched_lease_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_gates_worktree_lease.py::TestStampBaselineWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path / "elsewhere"))
        result = stamp_baseline(tmp_path, ())
        assert result.is_err
        assert result.danger_err == GateError.WorktreeLeaseViolation

    def test_no_lease_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_gates_worktree_lease.py::TestStampBaselineWorktreeLease.test_no_lease_succeeds  # noqa: E501
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        _init_repo(tmp_path)
        result = stamp_baseline(tmp_path, ())
        assert result.is_ok


class TestStampCoverageWorktreeLease:
    def test_mismatched_lease_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_gates_worktree_lease.py::TestStampCoverageWorktreeLease.test_mismatched_lease_refuses  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path / "elsewhere"))
        result = stamp_coverage(tmp_path)
        assert result.is_err
        assert result.danger_err == GateError.WorktreeLeaseViolation

    def test_no_lease_reaches_normal_missing_coverage_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_gates_worktree_lease.py::TestStampCoverageWorktreeLease.test_no_lease_reaches_normal_missing_coverage_error  # noqa: E501
        """With no lease set, the guard is a no-op -- the call proceeds to
        its ordinary logic (here, failing for the mundane reason of no
        coverage.xml present, NOT the lease guard)."""
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        _init_repo(tmp_path)
        result = stamp_coverage(tmp_path)
        assert result.is_err
        assert result.danger_err != GateError.WorktreeLeaseViolation
