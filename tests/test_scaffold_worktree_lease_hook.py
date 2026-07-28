"""T-0431: `install_worktree_lease_hook` -- pre-commit/pre-merge-commit
git hooks that abort a raw git commit/merge under FROB_AGENT."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from frob.scaffold import ScaffoldError, install_worktree_lease_hook


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "x.txt").write_text("x\n")
    _git("add", "-A", cwd=root)


# frob:ticket T-0731
class TestInstallWorktreeLeaseHook:
    def test_installs_pre_commit_and_pre_merge_commit(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_installs_pre_commit_and_pre_merge_commit  # noqa: E501
        _init_repo(tmp_path)
        result = install_worktree_lease_hook(tmp_path)
        assert result.is_ok
        paths = result.danger_ok
        names = {p.name for p in paths}
        assert names == {"pre-commit", "pre-merge-commit"}
        for path in paths:
            assert path.exists()
            assert os.access(path, os.X_OK)

    def test_refuses_existing_hook_without_force(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_refuses_existing_hook_without_force  # noqa: E501
        _init_repo(tmp_path)
        first = install_worktree_lease_hook(tmp_path)
        assert first.is_ok

        second = install_worktree_lease_hook(tmp_path)
        assert second.is_err
        assert second.danger_err == ScaffoldError.OutputExists

        forced = install_worktree_lease_hook(tmp_path, force=True)
        assert forced.is_ok

    def test_not_a_git_repo_fails(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_not_a_git_repo_fails  # noqa: E501
        not_a_repo = tmp_path / "not-a-repo"
        not_a_repo.mkdir()
        result = install_worktree_lease_hook(not_a_repo)
        assert result.is_err
        assert result.danger_err == ScaffoldError.NotAGitRepo

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_installed_hook_aborts_commit_under_frob_agent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_installed_hook_aborts_commit_under_frob_agent  # noqa: E501
        """End-to-end: a real `git commit` with FROB_AGENT set is aborted
        by the installed pre-commit hook (the exact incident acceptance
        case named in the ticket)."""
        _init_repo(tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        env = dict(os.environ, FROB_AGENT="test-agent-1")
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "should be blocked"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0
        assert "FROB_AGENT" in (commit.stdout + commit.stderr)

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_installed_hook_allows_commit_without_frob_agent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_installed_hook_allows_commit_without_frob_agent  # noqa: E501
        _init_repo(tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "coordinator commit"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_raw_merge_of_worktree_agent_branch_is_refused(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_raw_merge_of_worktree_agent_branch_is_refused  # noqa: E501
        """T-0577: even a COORDINATOR shell (no `FROB_AGENT` set -- the
        T-0431 guard's own exemption) must not be able to raw-merge a real
        merge commit for a `worktree-agent-*` ticket branch straight onto
        main; only `frob ticket land` (which never triggers this hook, see
        `_FORBID_RAW_TICKET_MERGE_SCRIPT`'s doc) is the sanctioned path."""
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        _git("branch", "worktree-agent-deadbeef", cwd=tmp_path)
        _git("checkout", "-q", "worktree-agent-deadbeef", cwd=tmp_path)
        (tmp_path / "y.txt").write_text("y\n")
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "ticket work", cwd=tmp_path)
        _git("checkout", "-q", "main", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        merged = subprocess.run(
            ["git", "merge", "--no-ff", "-m", "raw merge", "worktree-agent-deadbeef"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert merged.returncode != 0
        assert "worktree-agent-deadbeef" in (merged.stdout + merged.stderr)
        assert "frob ticket land" in (merged.stdout + merged.stderr)

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_raw_merge_override_env_var_allows_it(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_raw_merge_override_env_var_allows_it  # noqa: E501
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        _git("branch", "worktree-agent-deadbeef", cwd=tmp_path)
        _git("checkout", "-q", "worktree-agent-deadbeef", cwd=tmp_path)
        (tmp_path / "y.txt").write_text("y\n")
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "ticket work", cwd=tmp_path)
        _git("checkout", "-q", "main", cwd=tmp_path)

        env = dict(os.environ, FROB_LAND_INTERNAL="1")
        env.pop("FROB_AGENT", None)
        merged = subprocess.run(
            [
                "git",
                "merge",
                "--no-ff",
                "-m",
                "override merge",
                "worktree-agent-deadbeef",
            ],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert merged.returncode == 0, merged.stdout + merged.stderr

    # frob:ticket T-0731
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_land_owned_file_commit_refused_changelog(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_commit_refused_changelog  # noqa: E501
        """T-0731: a worktree commit touching CHANGELOG.md is refused --
        the changelog entry is land-generated, never hand-appended."""
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        (tmp_path / "CHANGELOG.md").write_text("## [0.1.0]\n\n- init\n")
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "hand-edit changelog"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0
        assert "CHANGELOG.md" in (commit.stdout + commit.stderr)
        assert "land-owned" in (commit.stdout + commit.stderr)

    # frob:ticket T-0731
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_land_owned_file_commit_refused_uv_lock(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_commit_refused_uv_lock  # noqa: E501
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        (tmp_path / "uv.lock").write_text("version = 1\n")
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "hand-edit lock"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0
        assert "uv.lock" in (commit.stdout + commit.stderr)

    # frob:ticket T-0731
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_land_owned_file_commit_refused_pyproject_version(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_commit_refused_pyproject_version  # noqa: E501
        """A `pyproject.toml` edit that touches the `version = "..."` line
        specifically is refused; an edit that leaves it alone is not."""
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n'
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.2.0"\n'
        )
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "hand-bump version"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0
        assert "version bump is land-owned" in (commit.stdout + commit.stderr)

    # frob:ticket T-0731
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_pyproject_edit_without_version_change_allowed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_pyproject_edit_without_version_change_allowed  # noqa: E501
        _init_repo(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\n'
        )
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "x"\nversion = "0.1.0"\ndescription = "y"\n'
        )
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "non-version pyproject edit"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr

    # frob:ticket T-0731
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_land_owned_file_override_env_var_allows_it(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_override_env_var_allows_it  # noqa: E501
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        (tmp_path / "CHANGELOG.md").write_text("## [0.1.0]\n\n- init\n")
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ, FROB_LAND_INTERNAL="1")
        env.pop("FROB_AGENT", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "land internal changelog write"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr

    # frob:ticket T-0731
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_tickets_md_change_warns_but_does_not_refuse(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_tickets_md_change_warns_but_does_not_refuse  # noqa: E501
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        (tmp_path / "tickets.md").write_text("# tickets\n")
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "hand-edit ledger"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr
        assert "WARNING" in (commit.stdout + commit.stderr)
        assert "tickets.md" in (commit.stdout + commit.stderr)
