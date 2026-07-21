"""T-0431: worktree-lease guard -- frob mutating commands fail LOUDLY when
FROB_WORKTREE names a worktree other than the cwd's actual git top-level.

Reproduces the real incident: a dispatched worktree agent ran `frob ticket
new` (and other mutating commands) directly against the shared main
checkout instead of its own worktree."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
from frob.tickets._models import TicketError
from frob.tickets._worktree_guard import FROB_WORKTREE_ENV, enforce_worktree_lease


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "tickets.md").write_text("# Tickets\n\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


class TestEnforceWorktreeLease:
    def test_no_env_var_is_unrestricted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_no_env_var_is_unrestricted  # noqa: E501
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        _init_repo(tmp_path)
        assert enforce_worktree_lease(tmp_path).is_ok

    def test_matching_worktree_passes(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_matching_worktree_passes  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path))
        assert enforce_worktree_lease(tmp_path).is_ok

    def test_mismatched_worktree_refuses(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_mismatched_worktree_refuses  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        elsewhere = tmp_path / "elsewhere-worktree"
        elsewhere.mkdir()

        monkeypatch.setenv(FROB_WORKTREE_ENV, str(elsewhere))
        result = enforce_worktree_lease(main_repo)
        assert result.is_err
        assert result.danger_err == TicketError.WorktreeLeaseViolation

    def test_non_repo_root_passes_through(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestEnforceWorktreeLease.test_non_repo_root_passes_through  # noqa: E501
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        monkeypatch.setenv(FROB_WORKTREE_ENV, str(tmp_path / "elsewhere"))
        assert enforce_worktree_lease(not_a_repo).is_ok


class TestWorktreeGuardWiredIntoMutations:
    """The acceptance case named in the ticket: a mutating command run from
    the WRONG checkout fails loudly; the same command from the leased
    worktree succeeds."""

    def _spec(self) -> TicketSpec:
        return TicketSpec(title="Guarded", kind=TicketKind.BUG, origin=Origin.AGENT)

    def test_new_ticket_from_main_while_leased_elsewhere_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations.test_new_ticket_from_main_while_leased_elsewhere_fails  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        worktree = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature", str(worktree), cwd=main_repo)

        monkeypatch.setenv(FROB_WORKTREE_ENV, str(worktree))
        result = new_ticket(main_repo, self._spec())
        assert result.is_err
        assert result.danger_err == TicketError.WorktreeLeaseViolation

    def test_new_ticket_from_leased_worktree_succeeds(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations.test_new_ticket_from_leased_worktree_succeeds  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        worktree = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature", str(worktree), cwd=main_repo)

        monkeypatch.setenv(FROB_WORKTREE_ENV, str(worktree))
        result = new_ticket(worktree, self._spec())
        assert result.is_ok

    def test_coordinator_with_no_lease_mutates_main_fine(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestWorktreeGuardWiredIntoMutations.test_coordinator_with_no_lease_mutates_main_fine  # noqa: E501
        monkeypatch.delenv(FROB_WORKTREE_ENV, raising=False)
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        result = new_ticket(main_repo, self._spec())
        assert result.is_ok
