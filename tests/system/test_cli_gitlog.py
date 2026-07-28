"""End-to-end tests for `frob gitlog`."""

import json
import subprocess
from pathlib import Path

from tests.system.conftest import run


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _setup_repo(tmp_path: Path) -> Path:
    """Create a git repo with conventional commits of mixed types."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    # frob:secret-fake reason="fabricated git identity for a test fixture repo"
    _git(["config", "user.email", "test@test.com"], repo)
    _git(["config", "user.name", "Test"], repo)

    def commit(msg: str) -> None:
        (repo / "file.txt").write_text(msg)
        _git(["add", "."], repo)
        _git(["commit", "-m", msg], repo)

    commit("chore: initial setup")
    commit("feat: add user authentication")
    commit("fix: handle null session token")
    commit("chore: update dependencies")
    _git(["tag", "v0.1.0"], repo)
    commit("refactor: extract token validator helper")
    commit("feat: add rate limiting")
    commit("fix: off-by-one in pagination")
    commit("feat!: remove legacy API endpoint")

    return repo


class TestGitlogLevels:
    def test_default_user_level_shows_feat_and_fix(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo))
        assert r.returncode == 0, r.stderr
        out = r.stdout + r.stderr
        assert "authentication" in out or "feat" in out.lower()
        assert "null session" in out or "fix" in out.lower()

    def test_default_user_level_excludes_chore(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo))
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "update dependencies" not in out

    def test_full_level_includes_chore(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "full")
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "update dependencies" in out or "chore" in out.lower()

    def test_full_level_includes_refactor(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "full")
        out = r.stdout + r.stderr
        assert "token validator" in out or "refactor" in out.lower()

    def test_changelog_level_shows_feat_and_fix(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "changelog")
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "authentication" in out or "feat" in out.lower()

    def test_changelog_level_excludes_refactor(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "changelog")
        out = r.stdout + r.stderr
        assert "token validator" not in out

    def test_major_level_shows_breaking_change(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "major")
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "legacy API" in out or "breaking" in out.lower() or "!" in out

    def test_major_level_excludes_regular_feat(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "major")
        out = r.stdout + r.stderr
        assert "rate limiting" not in out


class TestGitlogFilters:
    def test_since_tag_filters_older_commits(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "full", "--since", "v0.1.0")
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "initial setup" not in out
        assert "authentication" not in out

    def test_since_tag_includes_newer_commits(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "full", "--since", "v0.1.0")
        out = r.stdout + r.stderr
        assert "rate limiting" in out or "feat" in out.lower()

    def test_limit_n(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "full", "-n", "2")
        assert r.returncode == 0
        # With limit 2, many earlier commits should be absent
        out = r.stdout + r.stderr
        assert "initial setup" not in out

    def test_all_includes_non_conventional(self, tmp_path):
        repo = _setup_repo(tmp_path)
        # Add a non-conventional commit
        (repo / "readme.txt").write_text("some readme")
        _git(["add", "."], repo)
        _git(["commit", "-m", "added readme without type"], repo)

        r = run("gitlog", str(repo), "--level", "full", "--all")
        out = r.stdout + r.stderr
        assert "added readme without type" in out

    def test_without_all_excludes_non_conventional(self, tmp_path):
        repo = _setup_repo(tmp_path)
        (repo / "readme.txt").write_text("some readme")
        _git(["add", "."], repo)
        _git(["commit", "-m", "added readme without type"], repo)

        r = run("gitlog", str(repo), "--level", "full")
        out = r.stdout + r.stderr
        assert "added readme without type" not in out


class TestGitlogJson:
    def test_json_output_is_valid(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--json")
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert "commits" in data

    def test_json_commits_have_type_field(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "full", "--json")
        data = json.loads(r.stdout)
        assert len(data["commits"]) > 0
        for c in data["commits"]:
            assert "type" in c
            assert "sha" in c

    def test_json_breaking_commit_flagged(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("gitlog", str(repo), "--level", "full", "--json")
        data = json.loads(r.stdout)
        breaking = [c for c in data["commits"] if c.get("breaking")]
        assert len(breaking) >= 1


class TestGitlogErrors:
    def test_non_git_dir_returns_no_commits(self, tmp_path):
        r = run("gitlog", str(tmp_path))
        # frob gitlog on a non-git dir returns 0 with "no commits found"
        assert r.returncode == 0
        assert "no commits" in (r.stdout + r.stderr).lower()
