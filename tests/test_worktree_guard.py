"""T-0431: worktree-lease guard -- frob mutating commands fail LOUDLY when
FROB_WORKTREE names a worktree other than the cwd's actual git top-level.

Reproduces the real incident: a dispatched worktree agent ran `frob ticket
new` (and other mutating commands) directly against the shared main
checkout instead of its own worktree."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

import pytest

from frob.app.agent_runner import run as agent_run
from frob.gitio import GitError
from frob.scaffold._managed import _apply_stash_guard
from frob.tickets import Origin, TicketKind, TicketSpec, new_ticket
from frob.tickets._models import TicketError
from frob.tickets._worktree_guard import (
    FROB_AGENT_ENV,
    FROB_WORKTREE_ENV,
    agent_env_exports,
    enforce_worktree_lease,
)


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:waive DUP001 reason="parallel per-domain test scaffolding across \
# test_cli_evidence_enforcement.py, test_worktree_guard.py (2 sites) \
# -- each file exercises a structurally similar check for a distinct \
# domain/module with the same arrange-act shape; extracting would \
# blur which domain owns which check"
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


class TestAgentEnvExports:
    """T-0574: `agent_env_exports` resolves the FROB_WORKTREE/FROB_AGENT
    values `frob agent env` prints, mechanically instead of relying on a
    dispatcher/playbook to remember to set them by hand."""

    def test_resolves_worktree_root(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentEnvExports.test_resolves_worktree_root  # noqa: E501
        _init_repo(tmp_path)
        result = agent_env_exports(tmp_path)
        assert result.is_ok
        exports = result.danger_ok
        assert exports[FROB_WORKTREE_ENV] == str(tmp_path.resolve())
        assert exports[FROB_AGENT_ENV] == "1"

    def test_non_repo_root_errs(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentEnvExports.test_non_repo_root_errs  # noqa: E501
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        result = agent_env_exports(not_a_repo)
        assert result.is_err
        assert result.danger_err == GitError.NotARepo


class TestAgentRunnerEnv:
    """T-0574: `frob agent env` CLI wiring (`frob.app.agent_runner`)."""

    def test_env_prints_export_lines_for_worktree(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_prints_export_lines_for_worktree  # noqa: E501
        _init_repo(tmp_path)
        agent_run(["env", str(tmp_path)])
        out = capsys.readouterr().out
        assert f"export FROB_WORKTREE={shlex.quote(str(tmp_path.resolve()))}" in out
        assert f"export FROB_AGENT={shlex.quote('1')}" in out

    def test_env_defaults_to_cwd(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_defaults_to_cwd  # noqa: E501
        _init_repo(tmp_path)
        monkeypatch.chdir(tmp_path)
        agent_run(["env"])
        out = capsys.readouterr().out
        assert f"export FROB_WORKTREE={shlex.quote(str(tmp_path.resolve()))}" in out

    def test_env_non_repo_path_exits_nonzero(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        # frob:tests tests/test_worktree_guard.py::TestAgentRunnerEnv.test_env_non_repo_path_exits_nonzero  # noqa: E501
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        with pytest.raises(SystemExit) as excinfo:
            agent_run(["env", str(not_a_repo)])
        assert excinfo.value.code == 1


class TestStashGuardHook:
    """T-0574: the scaffold-managed `reference-transaction` hook that
    mechanically refuses `git stash` while sibling worktrees exist for the
    clone (docs/guides/agent-playbook.md#1b). `reference-transaction` is
    used (not an `alias.stash` override, and not the T-0431 `pre-commit`
    hooks) because both alternatives were verified NOT to intercept
    `git stash` at all -- see `frob.scaffold._managed`'s module-level
    comment for the empirical detail."""

    def test_refuses_stash_while_sibling_worktree_exists(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_refuses_stash_while_sibling_worktree_exists  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        assert _apply_stash_guard(main_repo).startswith(
            "hook reference-transaction: installed"
        )
        _git("worktree", "add", "-b", "feature", str(tmp_path / "wt"), cwd=main_repo)

        (main_repo / "tickets.md").write_text("# Tickets\n\nchanged\n")
        result = subprocess.run(
            ["git", "stash"], cwd=main_repo, capture_output=True, text=True
        )
        assert result.returncode != 0
        assert "refusing 'git stash'" in result.stderr

    def test_allows_stash_with_no_sibling_worktree(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_allows_stash_with_no_sibling_worktree  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        _apply_stash_guard(main_repo)

        (main_repo / "tickets.md").write_text("# Tickets\n\nchanged\n")
        result = subprocess.run(
            ["git", "stash"], cwd=main_repo, capture_output=True, text=True
        )
        assert result.returncode == 0

    def test_commit_is_unaffected_by_the_hook(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_commit_is_unaffected_by_the_hook  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        _apply_stash_guard(main_repo)
        _git("worktree", "add", "-b", "feature", str(tmp_path / "wt"), cwd=main_repo)

        (main_repo / "tickets.md").write_text("# Tickets\n\nchanged\n")
        _git("add", "-A", cwd=main_repo)
        result = subprocess.run(
            ["git", "commit", "-m", "test"], cwd=main_repo, capture_output=True
        )
        assert result.returncode == 0

    def test_idempotent_second_apply_is_noop(self, tmp_path: Path) -> None:
        # frob:tests tests/test_worktree_guard.py::TestStashGuardHook.test_idempotent_second_apply_is_noop  # noqa: E501
        main_repo = tmp_path / "main"
        _init_repo(main_repo)
        _apply_stash_guard(main_repo)
        assert (
            _apply_stash_guard(main_repo)
            == "hook reference-transaction: already current"
        )
