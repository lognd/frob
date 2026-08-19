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


# frob:ticket T-2556
def _setup_repo_with_worktree(tmp_path: Path) -> tuple[Path, Path]:
    """Init a repo with the lease hook installed and one linked worktree.

    Returns `(worktree_dir, root)`. T-2556's controls all need the same
    shape: a primary checkout plus at least one linked worktree, so that
    "is this the shared root?" is a question with a real answer.
    """
    root = tmp_path / "repo"
    _init_repo(root)
    _git("commit", "-q", "-m", "init", cwd=root)
    installed = install_worktree_lease_hook(root)
    assert installed.is_ok

    worktree_dir = tmp_path / "leased-worktree"
    added = _git(
        "worktree", "add", "-b", "agent-branch", str(worktree_dir), "main", cwd=root
    )
    assert added.returncode == 0, added.stdout + added.stderr
    return worktree_dir, root


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

    # frob:ticket T-2445
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_land_owned_file_commit_refused_changelog_fragment(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_land_owned_file_commit_refused_changelog_fragment  # noqa: E501
        """T-2445: a worktree commit touching `changelog.d/T-####.md` is
        refused, the same land-owned posture as `CHANGELOG.md` itself --
        `frob ticket land` writes fragments exclusively."""
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        (tmp_path / "changelog.d").mkdir()
        (tmp_path / "changelog.d" / "T-9999.md").write_text(
            "bump: minor\nT-9999: hand-edited\n"
        )
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "hand-write a changelog fragment"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0
        assert "changelog.d/T-9999.md" in (commit.stdout + commit.stderr)
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

    # frob:ticket T-1742
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_merge_commit_matching_main_is_allowed(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_merge_commit_matching_main_is_allowed  # noqa: E501
        """A `git merge main` merge commit that carries forward main's own
        land-generated CHANGELOG.md content -- byte-identical, no local
        divergence -- must not be refused by the land-owned-file guard."""
        _init_repo(tmp_path)
        (tmp_path / "CHANGELOG.md").write_text("## [0.1.0]\n\n- init\n")
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        # A sibling branch, forked before main advanced, simulating a
        # worktree that has not yet merged main's own later land.
        _git("branch", "-q", "feature", cwd=tmp_path)

        # main advances (as `frob ticket land` would) with a land-owned
        # CHANGELOG.md write, using the escape hatch land itself uses.
        env = dict(os.environ, FROB_LAND_INTERNAL="1")
        env.pop("FROB_AGENT", None)
        (tmp_path / "CHANGELOG.md").write_text("## [0.2.0]\n\n- landed thing\n")
        _git("add", "-A", cwd=tmp_path)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "land T-9999"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr

        # The worktree checks out its own branch and merges main forward --
        # the merge commit's staged CHANGELOG.md is byte-identical to
        # main's tip (fast-forward-able content, no local divergence).
        _git("checkout", "-q", "feature", cwd=tmp_path)
        merge_env = dict(os.environ)
        merge_env.pop("FROB_AGENT", None)
        merge_env.pop("FROB_LAND_INTERNAL", None)
        merge = subprocess.run(
            ["git", "merge", "--no-ff", "-q", "-m", "merge main", "main"],
            cwd=tmp_path,
            env=merge_env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert merge.returncode == 0, merge.stdout + merge.stderr

    # frob:ticket T-1742
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_merge_commit_diverging_from_main_still_refused(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_merge_commit_diverging_from_main_still_refused  # noqa: E501
        """A merge commit whose resolved CHANGELOG.md content DIFFERS from
        main's own tip (a hand-edit smuggled in via conflict resolution)
        is still refused -- the guard's real hazard is unweakened."""
        _init_repo(tmp_path)
        (tmp_path / "CHANGELOG.md").write_text("## [0.1.0]\n\n- init\n")
        _git("add", "-A", cwd=tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        _git("branch", "-q", "feature", cwd=tmp_path)

        env = dict(os.environ, FROB_LAND_INTERNAL="1")
        env.pop("FROB_AGENT", None)
        (tmp_path / "CHANGELOG.md").write_text("## [0.2.0]\n\n- landed thing\n")
        _git("add", "-A", cwd=tmp_path)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "land T-9999"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr

        # feature branch resolves the merge with its OWN hand-edited
        # content instead of taking main's -- this must still be refused.
        _git("checkout", "-q", "feature", cwd=tmp_path)
        merge_env = dict(os.environ)
        merge_env.pop("FROB_AGENT", None)
        merge_env.pop("FROB_LAND_INTERNAL", None)
        subprocess.run(
            ["git", "merge", "--no-ff", "--no-commit", "main"],
            cwd=tmp_path,
            env=merge_env,
            capture_output=True,
            text=True,
            check=False,
        )
        (tmp_path / "CHANGELOG.md").write_text("## [0.2.0]\n\n- hand-edited\n")
        _git("add", "-A", cwd=tmp_path)
        merge_commit = subprocess.run(
            ["git", "commit", "-q", "-m", "merge main (hand-edited)"],
            cwd=tmp_path,
            env=merge_env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert merge_commit.returncode != 0
        assert "CHANGELOG.md" in (merge_commit.stdout + merge_commit.stderr)
        assert "land-owned" in (merge_commit.stdout + merge_commit.stderr)

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

    # frob:ticket T-2071
    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    def test_agent_context_root_write_refused_without_frob_agent(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestInstallWorktreeLeaseHook.test_agent_context_root_write_refused_without_frob_agent  # noqa: E501
        """T-2071: `FROB_AGENT` is UNSET in every shell the Agent tool
        spawns, so the T-0431 guard above (keyed on that variable) never
        fires for the exact population it exists to stop. This reproduces
        the real incident shape: a linked worktree exists (an agent is
        dispatched), and a non-ledger source file is committed directly in
        the PRIMARY checkout with `FROB_AGENT` unset -- exactly what a
        dispatched agent's shell does. Must be refused on the fact that
        this is a root-checkout commit of a non-ledger file while
        worktrees exist, not on an env var nobody in this population
        sets."""
        _init_repo(tmp_path)
        _git("commit", "-q", "-m", "init", cwd=tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok

        worktree_dir = tmp_path.parent / "linked-worktree"
        added = _git(
            "worktree",
            "add",
            "-b",
            "agent-branch",
            str(worktree_dir),
            "main",
            cwd=tmp_path,
        )
        assert added.returncode == 0, added.stdout + added.stderr

        (tmp_path / "src_file.py").write_text("x = 1\n")
        _git("add", "-A", cwd=tmp_path)

        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "agent commits straight to root"],
            cwd=tmp_path,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode != 0, commit.stdout + commit.stderr
        assert "root" in (commit.stdout + commit.stderr).lower()


# frob:ticket T-2556
class TestFrobAgentGuardIsLocationAware:
    """T-2556: the FROB_AGENT guard refuses based on WHERE the commit
    lands, not on the variable alone.

    Before this ticket the guard was `if [ -n "$FROB_AGENT" ]` with no
    location test at all, so a commit inside the correctly-leased
    worktree -- including `frob ticket land`'s own pre-land wip commit --
    was refused exactly as hard as one against the shared root, and the
    printed remedy ("run from the leased worktree") could not work
    because the guard never looked at the path.

    The must-fire direction had a test
    (`test_installed_hook_aborts_commit_under_frob_agent`); the must-NOT-
    fire direction had none, in EITHER location, which is precisely how
    an unconditional guard passed review. Both directions are pinned
    here.
    """

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    # frob:ticket T-2556
    def test_commit_inside_leased_worktree_is_allowed(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware.test_commit_inside_leased_worktree_is_allowed  # noqa: E501
        """The must-NOT-fire control, and the one that would have caught
        the original defect: an agent-context commit in its OWN leased
        worktree is the sanctioned workflow and must be permitted."""
        worktree_dir, _ = _setup_repo_with_worktree(tmp_path)

        (worktree_dir / "agent_work.py").write_text("y = 2\n")
        _git("add", "-A", cwd=worktree_dir)
        env = dict(os.environ, FROB_AGENT="1", FROB_WORKTREE=str(worktree_dir))
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "agent commits in its own worktree"],
            cwd=worktree_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    # frob:ticket T-2556
    def test_commit_against_shared_root_is_still_refused(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware.test_commit_against_shared_root_is_still_refused  # noqa: E501
        """The must-fire control: T-0431's whole purpose. Narrowing the
        guard to a location test must not hand the shared root back."""
        _worktree_dir, root = _setup_repo_with_worktree(tmp_path)

        (root / "stray.py").write_text("z = 3\n")
        _git("add", "-A", cwd=root)
        env = dict(os.environ, FROB_AGENT="1")
        env.pop("FROB_WORKTREE", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "agent commits straight to the root"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        output = commit.stdout + commit.stderr
        assert commit.returncode != 0, output
        assert "SHARED ROOT" in output

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    # frob:ticket T-2556
    def test_refusal_names_a_remedy_that_actually_works(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware.test_refusal_names_a_remedy_that_actually_works  # noqa: E501
        """Defect 2 was the message, not just the condition: it advised
        "run from the leased worktree" while the guard ignored the path,
        so anyone following it failed again identically. This pins the
        advice to the behaviour -- the root refusal points at the
        worktree, and `test_commit_inside_leased_worktree_is_allowed`
        proves that pointer resolves to a working commit."""
        _worktree_dir, root = _setup_repo_with_worktree(tmp_path)

        (root / "stray2.py").write_text("z = 4\n")
        _git("add", "-A", cwd=root)
        env = dict(os.environ, FROB_AGENT="1")
        env.pop("FROB_WORKTREE", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "stray root commit"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        output = commit.stdout + commit.stderr
        assert commit.returncode != 0, output
        assert "leased worktree" in output
        assert "frob ticket work" in output

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    # frob:ticket T-2556
    def test_commit_in_a_worktree_other_than_the_leased_one_is_refused(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware.test_commit_in_a_worktree_other_than_the_leased_one_is_refused  # noqa: E501
        """Being in SOME worktree is not enough: an agent leasing one
        worktree must not commit into a sibling agent's checkout."""
        leased, root = _setup_repo_with_worktree(tmp_path)
        other = tmp_path / "other-worktree"
        added = _git("worktree", "add", "-b", "other-branch", str(other), "main", cwd=root)
        assert added.returncode == 0, added.stdout + added.stderr

        (other / "trespass.py").write_text("w = 5\n")
        _git("add", "-A", cwd=other)
        env = dict(os.environ, FROB_AGENT="1", FROB_WORKTREE=str(leased))
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "commit into a sibling's worktree"],
            cwd=other,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        output = commit.stdout + commit.stderr
        assert commit.returncode != 0, output
        assert "NOT the leased" in output

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    # frob:ticket T-2556
    def test_coordinator_commit_unaffected_in_both_locations(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware.test_coordinator_commit_unaffected_in_both_locations  # noqa: E501
        """A coordinator shell (FROB_AGENT unset) is untouched by this
        guard in the worktree. Its root behaviour is owned by the
        separate T-2071 check, which
        `test_agent_context_root_write_refused_without_frob_agent`
        already pins."""
        worktree_dir, _root = _setup_repo_with_worktree(tmp_path)

        (worktree_dir / "coord.py").write_text("c = 6\n")
        _git("add", "-A", cwd=worktree_dir)
        env = dict(os.environ)
        env.pop("FROB_AGENT", None)
        env.pop("FROB_WORKTREE", None)
        env.pop("FROB_LAND_INTERNAL", None)
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "coordinator commit in worktree"],
            cwd=worktree_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr

    @pytest.mark.skipif(os.name == "nt", reason="POSIX shell hook, not run on Windows")
    # frob:ticket T-2556
    def test_land_internal_commit_in_root_is_exempt(self, tmp_path: Path) -> None:
        # frob:tests tests/test_scaffold_worktree_lease_hook.py::TestFrobAgentGuardIsLocationAware.test_land_internal_commit_in_root_is_exempt  # noqa: E501
        """`frob ticket land` commits in the primary checkout as part of
        its normal operation and marks those commits with
        FROB_LAND_INTERNAL, the same escape hatch the T-2071 guard
        already honours."""
        _worktree_dir, root = _setup_repo_with_worktree(tmp_path)

        (root / "landed.py").write_text("v = 7\n")
        _git("add", "-A", cwd=root)
        env = dict(os.environ, FROB_AGENT="1", FROB_LAND_INTERNAL="1")
        commit = subprocess.run(
            ["git", "commit", "-q", "-m", "land machinery commit"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        assert commit.returncode == 0, commit.stdout + commit.stderr


# frob:ticket T-2565
class TestOursMarkerMigration:
    """T-2565: the hook's "this one is mine" marker named a command that
    never existed (`frob scaffold install-worktree-lease-hook`; the real
    installer is `frob scaffold apply`).

    Retiring it is a migration, not a string edit: the marker is how frob
    recognises a hook it owns, so a straight rename would make every
    ALREADY-INSTALLED hook read as a repo's own custom file -- never
    updated again and never reported stale. Both directions are pinned.
    """

    # frob:ticket T-2565
    def test_current_marker_names_a_real_command(self) -> None:
        from frob.scaffold._managed import _OURS_MARKER

        assert "install-worktree-lease-hook" not in _OURS_MARKER
        assert "frob scaffold apply" in _OURS_MARKER

    # frob:ticket T-2565
    def test_installed_hook_carries_the_current_marker(self, tmp_path: Path) -> None:
        from frob.scaffold._managed import _OURS_MARKER

        _init_repo(tmp_path)
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok
        body = (tmp_path / ".git" / "hooks" / "pre-commit").read_text()
        assert _OURS_MARKER in body

    # frob:ticket T-2565
    def test_legacy_marker_still_recognised_as_ours(self) -> None:
        """The migration control. A hook installed by an older frob must
        keep being recognised, or it silently stops being maintained."""
        from frob.scaffold._managed import _LEGACY_OURS_MARKERS, _is_ours

        assert _LEGACY_OURS_MARKERS
        for legacy in _LEGACY_OURS_MARKERS:
            assert _is_ours(f"#!/bin/sh\n{legacy}\nexit 0\n")

    # frob:ticket T-2565
    def test_a_foreign_hook_is_not_claimed(self) -> None:
        """The must-NOT-fire direction: widening recognition must not
        start claiming a repo's own custom hook, which would then be
        overwritten."""
        from frob.scaffold._managed import _is_ours

        assert not _is_ours("#!/bin/sh\n# our own project hook\nexit 0\n")

    # frob:ticket T-2565
    def test_a_legacy_installed_hook_is_reported_stale_not_foreign(
        self, tmp_path: Path
    ) -> None:
        """End to end: a hook carrying the OLD marker is still ours, so
        it is reported as stale (updatable) rather than left alone
        forever as somebody else's file."""
        from frob.scaffold._managed import _LEGACY_OURS_MARKERS, scaffold_conformance_status

        _init_repo(tmp_path)
        # scaffold_conformance_status skips a tree with no frob.toml.
        (tmp_path / "frob.toml").write_text("[frob]\n")
        installed = install_worktree_lease_hook(tmp_path)
        assert installed.is_ok
        hook = tmp_path / ".git" / "hooks" / "pre-commit"
        hook.write_text(f"#!/bin/sh\n{_LEGACY_OURS_MARKERS[0]}\nexit 0\n")

        statuses = [
            s for s in scaffold_conformance_status(tmp_path) if s.block_id == "hook-pre-commit"
        ]
        assert statuses, "pre-commit hook status not reported"
        assert statuses[0].present
        assert statuses[0].stale
