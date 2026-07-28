"""Tests for frob.gitio -- the one git subprocess seam (docs/modules/testing.md)."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Any

import pytest

from frob.gitio import (
    GitError,
    common_dir_and_branch,
    current_branch,
    git_common_dir,
    repo_root,
    reset_common_dir_cache,
    run_argv,
    spawn_recorder,
    working_diff,
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _commit(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


class TestRepoRoot:
    def test_main_checkout(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::repo_root
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.txt").write_text("hello\n")
        _commit(repo, "init")

        result = repo_root(repo)
        assert result.is_ok
        assert result.danger_ok.resolve() == repo.resolve()

    def test_linked_worktree_resolves_to_worktree_root(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.txt").write_text("hello\n")
        _commit(repo, "init")

        wt = tmp_path / "wt"
        _git(repo, "worktree", "add", "-b", "feature", str(wt))

        result = repo_root(wt)
        assert result.is_ok
        assert result.danger_ok.resolve() == wt.resolve()

    def test_not_a_repo(self, tmp_path: Path) -> None:
        outside = tmp_path / "not-a-repo"
        outside.mkdir()
        result = repo_root(outside)
        assert result.is_err
        assert result.danger_err == GitError.NotARepo

    def test_nonexistent_path_is_not_a_repo(self, tmp_path: Path) -> None:
        """A `start` path that does not exist at all short-circuits before
        ever spawning git."""
        missing = tmp_path / "does-not-exist-at-all"
        result = repo_root(missing)
        assert result.is_err
        assert result.danger_err == GitError.NotARepo

    def test_run_argv_failure_surfaces_as_not_a_repo(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """If the underlying `run_argv` spawn itself fails (not just a
        nonzero git exit), `repo_root` still reports `NotARepo`."""
        import frob.gitio as gitio_mod

        monkeypatch.setattr(
            gitio_mod,
            "run_argv",
            lambda argv, **kw: gitio_mod.Err(GitError.GitFailed),
        )
        result = repo_root(tmp_path)
        assert result.is_err
        assert result.danger_err == GitError.NotARepo


class TestWorkingDiff:
    def test_covers_committed_staged_unstaged_and_untracked(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gitio.py::working_diff
        # frob:tests src/frob/gitio.py kind="integration"
        # Exercises gitio's real git subprocess seam end to end (init,
        # commit, stage, and untracked state) against a live repo, not a
        # mocked subprocess.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "base.py").write_text("x = 1\n")
        _commit(repo, "base")

        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "committed.py").write_text("y = 2\n")
        _commit(repo, "committed change")

        (repo / "staged.py").write_text("z = 3\n")
        _git(repo, "add", "staged.py")

        (repo / "base.py").write_text("x = 1\nx = 2\n")

        (repo / "untracked.py").write_text("w = 4\n")

        result = working_diff(repo, "main")
        assert result.is_ok
        diff = result.danger_ok

        files = {hunk.file for hunk in diff.hunks}
        assert files == {"committed.py", "staged.py", "base.py", "untracked.py"}

    def test_untracked_directory_is_skipped_not_read_as_file(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests src/frob/gitio.py::working_diff
        # Regression for T-0227: an untracked gitlink/nested-worktree dir
        # (e.g. .claude/worktrees/x) is listed by `ls-files --others` like a
        # file, but reading it raises Errno 21 (Is a directory). It must be
        # skipped cleanly rather than surfaced as a warning.
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "base.py").write_text("x = 1\n")
        _commit(repo, "base")

        (repo / "untracked.py").write_text("w = 4\n")
        nested = repo / "nested-worktree"
        _init_repo(nested)
        (nested / "inner.txt").write_text("irrelevant\n")
        _commit(nested, "inner")

        with caplog.at_level(logging.WARNING):
            result = working_diff(repo, "main")

        assert result.is_ok
        diff = result.danger_ok
        files = {hunk.file for hunk in diff.hunks}
        assert files == {"untracked.py"}
        assert not any(
            "could not read untracked file" in record.message
            for record in caplog.records
        )

    def test_merge_base_not_head(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "base.py").write_text("x = 1\n")
        _commit(repo, "base")

        _git(repo, "checkout", "-q", "-b", "feature")
        (repo / "feat.py").write_text("y = 1\n")
        _commit(repo, "feature commit")

        # advance main so HEAD-of-main diverges from the merge-base too.
        _git(repo, "checkout", "-q", "main")
        (repo / "mainonly.py").write_text("q = 1\n")
        _commit(repo, "main-only commit")
        _git(repo, "checkout", "-q", "feature")

        result = working_diff(repo, "main")
        assert result.is_ok
        diff = result.danger_ok
        files = {hunk.file for hunk in diff.hunks}
        assert "feat.py" in files
        assert "mainonly.py" not in files

    def test_hunk_paths_are_repo_relative_posix(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "base.py").write_text("x = 1\n")
        _commit(repo, "base")

        _git(repo, "checkout", "-q", "-b", "feature")
        sub = repo / "pkg"
        sub.mkdir()
        (sub / "mod.py").write_text("a = 1\n")
        _commit(repo, "add pkg/mod.py")

        result = working_diff(repo, "main")
        assert result.is_ok
        files = {hunk.file for hunk in result.danger_ok.hunks}
        assert "pkg/mod.py" in files

    def test_bad_base_ref_is_git_failed(self, tmp_path: Path) -> None:
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "base.py").write_text("x = 1\n")
        _commit(repo, "base")

        result = working_diff(repo, "does-not-exist")
        assert result.is_err
        assert result.danger_err == GitError.GitFailed

    def test_diff_command_failure_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failing `git diff` invocation (after a successful merge-base)
        propagates its error rather than being swallowed."""
        import frob.gitio as gitio_mod

        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "base.py").write_text("x = 1\n")
        _commit(repo, "base")

        real_run_git = gitio_mod._run_git

        def flaky_run_git(args, *, cwd, timeout_s=gitio_mod._DEFAULT_TIMEOUT_S):
            if args and args[0] == "diff":
                return gitio_mod.Err(GitError.GitFailed)
            return real_run_git(args, cwd=cwd, timeout_s=timeout_s)

        monkeypatch.setattr(gitio_mod, "_run_git", flaky_run_git)
        result = working_diff(repo, "main")
        assert result.is_err
        assert result.danger_err == GitError.GitFailed

    def test_untracked_listing_failure_propagates(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A failing `git ls-files --others` invocation propagates its
        error, distinct from the `git diff` failure path above."""
        import frob.gitio as gitio_mod

        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "base.py").write_text("x = 1\n")
        _commit(repo, "base")

        real_run_git = gitio_mod._run_git

        def flaky_run_git(args, *, cwd, timeout_s=gitio_mod._DEFAULT_TIMEOUT_S):
            if args and args[0] == "ls-files":
                return gitio_mod.Err(GitError.GitFailed)
            return real_run_git(args, cwd=cwd, timeout_s=timeout_s)

        monkeypatch.setattr(gitio_mod, "_run_git", flaky_run_git)
        result = working_diff(repo, "main")
        assert result.is_err
        assert result.danger_err == GitError.GitFailed


class TestRunArgv:
    def test_captures_stdout_and_zero_returncode(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::run_argv
        result = run_argv(["echo", "hello"], cwd=tmp_path)
        assert result.is_ok
        proc = result.danger_ok
        assert proc.returncode == 0
        assert proc.stdout.strip() == "hello"

    def test_nonzero_returncode_is_ok_not_err(self, tmp_path: Path) -> None:
        # a nonzero exit is data (ProcResult), not a spawn failure
        result = run_argv(["sh", "-c", "exit 3"], cwd=tmp_path)
        assert result.is_ok
        assert result.danger_ok.returncode == 3

    def test_nonexistent_binary_is_git_failed(self, tmp_path: Path) -> None:
        result = run_argv(["/no/such/binary"], cwd=tmp_path)
        assert result.is_err
        assert result.danger_err == GitError.GitFailed

    def test_timeout_is_git_failed(self, tmp_path: Path) -> None:
        result = run_argv(["sleep", "5"], cwd=tmp_path, timeout_s=0.2)
        assert result.is_err
        assert result.danger_err == GitError.GitFailed

    def test_kill_switch_refuses_without_spawning(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests src/frob/gitio.py::run_argv
        # T-0778: FROB_DISABLE_EXEC=1 must make run_argv refuse to spawn
        # (Result error, logged) rather than partially bypass the T-0200
        # guard -- this is the audit H2 gap this ticket closes: run_argv is
        # gitio's single spawn seam, reused by the serve daemon and every
        # gitio-based lease read, so guarding it here covers all three.
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = subprocess.run

        def _spy(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr(subprocess, "run", _spy)
        with caplog.at_level(logging.WARNING):
            result = run_argv(["echo", "hello"], cwd=tmp_path)
        assert result.is_err
        assert result.danger_err == GitError.GitFailed
        assert not spawned
        assert any("exec disabled" in record.message for record in caplog.records)


class TestCurrentBranch:
    def test_returns_branch_name(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::current_branch
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.txt").write_text("hello\n")
        _commit(repo, "init")

        result = current_branch(repo)
        assert result.is_ok
        assert result.danger_ok == "main"


# frob:ticket T-0784
class TestGitCommonDir:
    def test_resolves_absolute_common_dir(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::git_common_dir kind="unit"
        reset_common_dir_cache()
        repo = tmp_path / "repo"
        _init_repo(repo)

        result = git_common_dir(repo)
        assert result.is_ok
        common = result.danger_ok
        assert common.is_absolute()
        assert common == (repo / ".git").resolve()

    def test_err_when_not_a_repo(self, tmp_path: Path) -> None:
        reset_common_dir_cache()
        not_a_repo = tmp_path / "plain"
        not_a_repo.mkdir()

        result = git_common_dir(not_a_repo)
        assert result.is_err
        assert result.danger_err is GitError.GitFailed

    def test_memoized_per_root(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::git_common_dir kind="unit"
        reset_common_dir_cache()
        repo = tmp_path / "repo"
        _init_repo(repo)

        with spawn_recorder() as recorder:
            first = git_common_dir(repo)
            second = git_common_dir(repo)

        assert first.is_ok
        assert first.danger_ok == second.danger_ok
        spawn_count = sum(
            n for argv, n in recorder.counts().items() if "--git-common-dir" in argv
        )
        assert spawn_count == 1

    def test_reset_clears_cache(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::reset_common_dir_cache kind="unit"
        reset_common_dir_cache()
        repo = tmp_path / "repo"
        _init_repo(repo)
        git_common_dir(repo)
        reset_common_dir_cache()

        with spawn_recorder() as recorder:
            git_common_dir(repo)

        spawn_count = sum(
            n for argv, n in recorder.counts().items() if "--git-common-dir" in argv
        )
        assert spawn_count == 1


# frob:ticket T-0784
class TestCommonDirAndBranch:
    def test_single_spawn_parses_both_lines(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::common_dir_and_branch kind="unit"
        repo = tmp_path / "repo"
        _init_repo(repo)
        (repo / "a.txt").write_text("hello\n")
        _commit(repo, "init")

        with spawn_recorder() as recorder:
            result = common_dir_and_branch(repo)

        assert result.is_ok
        common, branch = result.danger_ok
        assert common == (repo / ".git").resolve()
        assert branch == "main"
        assert sum(recorder.counts().values()) == 1

    def test_err_when_not_a_repo(self, tmp_path: Path) -> None:
        not_a_repo = tmp_path / "plain"
        not_a_repo.mkdir()

        result = common_dir_and_branch(not_a_repo)
        assert result.is_err
        assert result.danger_err is GitError.GitFailed


# frob:ticket T-0776
class TestSpawnRecorder:
    def test_tallies_spawns_made_inside_the_block(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::spawn_recorder kind="unit"
        # frob:tests src/frob/gitio.py::SpawnRecorder.record kind="unit"
        # frob:tests src/frob/gitio.py::SpawnRecorder.counts kind="unit"
        with spawn_recorder() as recorder:
            run_argv(["echo", "one"], cwd=tmp_path)
            run_argv(["echo", "one"], cwd=tmp_path)
            run_argv(["echo", "two"], cwd=tmp_path)

        assert recorder.counts() == {
            ("echo", "one"): 2,
            ("echo", "two"): 1,
        }

    def test_spawns_outside_the_block_are_not_tallied(self, tmp_path: Path) -> None:
        with spawn_recorder() as recorder:
            run_argv(["echo", "inside"], cwd=tmp_path)
        run_argv(["echo", "outside"], cwd=tmp_path)

        assert recorder.counts() == {("echo", "inside"): 1}

    def test_duplicates_reports_only_argvs_over_budget(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gitio.py::SpawnRecorder.duplicates kind="unit"
        with spawn_recorder() as recorder:
            run_argv(["echo", "once"], cwd=tmp_path)
            run_argv(["echo", "twice"], cwd=tmp_path)
            run_argv(["echo", "twice"], cwd=tmp_path)

        assert recorder.duplicates() == {("echo", "twice"): 2}

    def test_duplicates_honors_a_declared_per_argv_budget(self, tmp_path: Path) -> None:
        argv = ("echo", "expected-twice")
        with spawn_recorder() as recorder:
            run_argv(list(argv), cwd=tmp_path)
            run_argv(list(argv), cwd=tmp_path)

        assert recorder.duplicates({argv: 2}) == {}

    def test_run_argv_outside_any_recorder_does_not_raise(self, tmp_path: Path) -> None:
        # zero-cost/behavior-neutral when disabled: no active recorder must
        # never change what run_argv spawns or returns.
        result = run_argv(["echo", "no-recorder"], cwd=tmp_path)
        assert result.is_ok
        assert result.danger_ok.stdout.strip() == "no-recorder"
