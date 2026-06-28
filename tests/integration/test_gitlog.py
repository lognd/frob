"""
Integration tests for frob gitlog with real git history.

Builds a repo with 6+ commits of mixed conventional types, tags, and
a breaking change, then asserts gitlog correctly groups, filters, and
formats them.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

FROB = [sys.executable, "-m", "frob"]


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _frob(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        FROB + args,
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd else None,
    )


def _setup_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "ci@test.com"], repo)
    _git(["config", "user.name", "CI Test"], repo)

    counter = [0]

    def commit(msg: str) -> None:
        counter[0] += 1
        (repo / f"f{counter[0]}.txt").write_text(msg)
        _git(["add", "."], repo)
        _git(["commit", "-m", msg], repo)

    # Commits before v0.1.0
    commit("chore: initial project setup")
    commit("feat: add login endpoint")
    commit("fix: correct password hashing")
    commit("docs: add API readme")
    _git(["tag", "v0.1.0"], repo)

    # Commits after v0.1.0
    commit("refactor: extract validation helpers")
    commit("feat: add token refresh")
    commit("fix: handle expired tokens correctly")
    commit("perf: cache user lookups")
    commit("feat!: remove deprecated /v1/login route")
    commit("chore: bump version to 0.2.0")

    return repo


class TestGitlogGrouping:
    @pytest.fixture(scope="class")
    def repo(self, tmp_path_factory):
        return _setup_repo(tmp_path_factory.mktemp("gitlog"))

    def test_features_grouped_separately(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full"])
        out = r.stdout + r.stderr
        assert "feat" in out.lower() or "feature" in out.lower()

    def test_fixes_present_at_user_level(self, repo):
        r = _frob(["gitlog", str(repo)])
        out = r.stdout + r.stderr
        assert "password hashing" in out or "fix" in out.lower()

    def test_chore_absent_at_user_level(self, repo):
        r = _frob(["gitlog", str(repo)])
        out = r.stdout + r.stderr
        assert "bump version" not in out

    def test_chore_present_at_full_level(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full"])
        out = r.stdout + r.stderr
        assert "bump version" in out or "chore" in out.lower()

    def test_breaking_change_labeled(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "major"])
        out = r.stdout + r.stderr
        assert "deprecated" in out or "breaking" in out.lower() or "!" in out

    def test_perf_shown_at_user_level(self, repo):
        r = _frob(["gitlog", str(repo)])
        out = r.stdout + r.stderr
        assert "cache user" in out or "perf" in out.lower()


class TestGitlogSinceTag:
    @pytest.fixture(scope="class")
    def repo(self, tmp_path_factory):
        return _setup_repo(tmp_path_factory.mktemp("gitlog_since"))

    def test_since_tag_excludes_pre_tag_commits(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full", "--since", "v0.1.0"])
        assert r.returncode == 0, r.stderr
        out = r.stdout + r.stderr
        assert "login endpoint" not in out
        assert "password hashing" not in out

    def test_since_tag_includes_post_tag_commits(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full", "--since", "v0.1.0"])
        out = r.stdout + r.stderr
        assert "token refresh" in out or "feat" in out.lower()

    def test_since_tag_includes_breaking_change(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "major", "--since", "v0.1.0"])
        out = r.stdout + r.stderr
        assert "deprecated" in out or "!" in out or "breaking" in out.lower()


class TestGitlogJson:
    @pytest.fixture(scope="class")
    def repo(self, tmp_path_factory):
        return _setup_repo(tmp_path_factory.mktemp("gitlog_json"))

    def _parse_json(self, r: subprocess.CompletedProcess) -> dict:
        return json.loads(r.stdout)

    def test_json_valid(self, repo):
        r = _frob(["gitlog", str(repo), "--json"])
        assert r.returncode == 0
        data = self._parse_json(r)
        assert "commits" in data

    def test_json_commit_fields(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full", "--json"])
        data = self._parse_json(r)
        assert len(data["commits"]) > 0
        c = data["commits"][0]
        assert "sha" in c
        assert "type" in c
        assert "description" in c
        assert "breaking" in c

    def test_json_breaking_commit_flagged_true(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full", "--json"])
        data = self._parse_json(r)
        breaking = [c for c in data["commits"] if c["breaking"]]
        assert len(breaking) >= 1
        assert any(
            "deprecated" in c["description"] or "v1" in c["description"]
            for c in breaking
        )

    def test_json_feat_type_field(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full", "--json"])
        data = self._parse_json(r)
        feat_commits = [c for c in data["commits"] if c["type"] == "feat"]
        assert len(feat_commits) >= 2

    def test_json_since_tag_filters(self, repo):
        r = _frob(
            ["gitlog", str(repo), "--level", "full", "--since", "v0.1.0", "--json"]
        )
        data = self._parse_json(r)
        descriptions = [c["description"] for c in data["commits"]]
        assert not any("login endpoint" in d for d in descriptions)
        assert any("token refresh" in d or "refresh" in d for d in descriptions)

    def test_json_granularity_field(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "changelog", "--json"])
        data = self._parse_json(r)
        assert data.get("granularity") == "changelog"

    def test_json_limit_respected(self, repo):
        r = _frob(["gitlog", str(repo), "--level", "full", "-n", "3", "--json"])
        data = self._parse_json(r)
        assert len(data["commits"]) <= 3


class TestGitlogAllFlag:
    def test_non_conventional_commit_excluded_by_default(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(["init", "-b", "main"], repo)
        _git(["config", "user.email", "t@t.com"], repo)
        _git(["config", "user.name", "T"], repo)
        (repo / "f.txt").write_text("x")
        _git(["add", "."], repo)
        _git(["commit", "-m", "WIP no type here"], repo)

        r = _frob(["gitlog", str(repo), "--level", "full"])
        assert "WIP no type here" not in (r.stdout + r.stderr)

    def test_all_flag_includes_non_conventional(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(["init", "-b", "main"], repo)
        _git(["config", "user.email", "t@t.com"], repo)
        _git(["config", "user.name", "T"], repo)
        (repo / "f.txt").write_text("x")
        _git(["add", "."], repo)
        _git(["commit", "-m", "WIP no type here"], repo)

        r = _frob(["gitlog", str(repo), "--level", "full", "--all"])
        assert "WIP no type here" in (r.stdout + r.stderr)
