"""
Unit tests for frob.gitlog.git_log calling the library function directly
(not via CLI subprocess).
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

import pytest

from frob.gitlog import git_log


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    # frob:secret-fake reason="fabricated git identity for a test fixture repo"
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "tester"], cwd=path, check=True)
    (path / "f.txt").write_text("one\n")
    subprocess.run(["git", "add", "f.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "feat: add first feature"], cwd=path, check=True
    )
    (path / "f.txt").write_text("two\n")
    subprocess.run(["git", "add", "f.txt"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "chore: bump version"], cwd=path, check=True
    )


def test_git_log(tmp_path: Path) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    _init_repo(tmp_path)

    result = git_log(tmp_path, granularity="full")

    types = {c.type for c in result.commits}
    assert "feat" in types
    assert "chore" in types

    user_result = git_log(tmp_path, granularity="user")
    assert all(c.type != "chore" for c in user_result.commits)


def test_git_log_include_non_conventional_keeps_unknown_type(
    tmp_path: Path,
) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    # Proves the `include_non_conventional=True` branch: a subject that does
    # not match the conventional-commit grammar is normally dropped, but
    # survives when the caller opts in.
    _init_repo(tmp_path)
    (tmp_path / "f.txt").write_text("three\n")
    subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "not a conventional subject"],
        cwd=tmp_path,
        check=True,
    )

    default_result = git_log(tmp_path, granularity="full")
    assert all(c.type != "unknown" for c in default_result.commits)

    full_result = git_log(tmp_path, granularity="full", include_non_conventional=True)
    assert any(c.type == "unknown" for c in full_result.commits)


def test_git_log_since_tag_form_uses_range_syntax(tmp_path: Path) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    # Proves the `since` value starting with "v" is treated as a tag/ref and
    # passed as a `<since>..HEAD` range instead of a `--since=<date>` filter.
    _init_repo(tmp_path)
    subprocess.run(["git", "tag", "v1.0.0"], cwd=tmp_path, check=True)
    (tmp_path / "f.txt").write_text("three\n")
    subprocess.run(["git", "add", "f.txt"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "fix: patch after tag"],
        cwd=tmp_path,
        check=True,
    )

    result = git_log(tmp_path, granularity="full", since="v1.0.0")
    descriptions = {c.description for c in result.commits}
    assert "patch after tag" in descriptions
    assert "add first feature" not in descriptions


def test_git_log_until_and_limit_filter_output(tmp_path: Path) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    # Proves the `until` and `limit` args are actually threaded through to
    # the underlying `git log` invocation (not just accepted and ignored).
    _init_repo(tmp_path)

    limited = git_log(tmp_path, granularity="full", limit=1)
    assert len(limited.commits) == 1

    far_past = git_log(tmp_path, granularity="full", until="1970-01-01")
    assert far_past.commits == []


def test_git_log_missing_git_binary_returns_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    # Proves the FileNotFoundError path in `_git_log_raw`: when the `git`
    # binary itself cannot be found, `git_log` degrades to an empty result
    # instead of propagating the exception.
    from frob import gitlog as gitlog_module

    def _raise(*args: object, **kwargs: object) -> object:
        raise FileNotFoundError("git")

    monkeypatch.setattr(gitlog_module, "guarded_subprocess_run", _raise)
    result = git_log(Path("."), granularity="full")
    assert result.commits == []


# frob:ticket T-0803
def test_git_log_kill_switch_refuses_without_spawning(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # frob:tests src/frob/gitlog/__init__.py::git_log kind="unit"
    # T-0803: FROB_DISABLE_EXEC=1 must make git_log's underlying `git log`
    # spawn refuse (via guarded_subprocess_run) instead of bypassing the
    # T-0200/T-0778 exec guard -- proven with a spy on the real
    # `subprocess.run` so a spawn attempt would be observed, not assumed.
    _init_repo(tmp_path)
    monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
    spawned = False
    real_run = subprocess.run

    def _spy(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        nonlocal spawned
        spawned = True
        return real_run(*args, **kwargs)

    monkeypatch.setattr(subprocess, "run", _spy)
    result = git_log(tmp_path, granularity="full")
    assert not spawned
    assert list(result.commits) == []
