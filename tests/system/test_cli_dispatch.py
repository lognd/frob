"""End-to-end tests for `frob dispatch` (create/list/abort).

collect is tested in tests/integration/test_dispatch_edit.py since it
requires committing inside the worktree and a full git round-trip.
"""

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
    """Create a minimal git repo with one commit. Returns repo root."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "test@test.com"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "pyproject.toml").write_text(
        '[project]\nname = "test"\nversion = "0.1.0"\n'
    )
    _git(["add", "."], repo)
    _git(["commit", "-m", "init: initial commit"], repo)
    return repo


def _parse_dispatch_id(output: str) -> str:
    for line in output.splitlines():
        if line.startswith("dispatch "):
            return line.split()[1]
    raise AssertionError(f"no dispatch id in: {output!r}")


class TestDispatchCreate:
    def test_create_returns_id_and_worktree(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "fix-bug", cwd=repo)
        assert r.returncode == 0, r.stderr
        out = r.stdout + r.stderr
        assert "dispatch " in out
        assert "worktree:" in out

    def test_creates_worktree_directory(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "add-feature", cwd=repo)
        assert r.returncode == 0, r.stderr
        for line in (r.stdout + r.stderr).splitlines():
            if "worktree:" in line:
                wt = Path(line.split("worktree:")[1].strip())
                assert wt.exists()
                return
        raise AssertionError("no worktree line in output")

    def test_creates_state_file(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "my-label", cwd=repo)
        assert r.returncode == 0, r.stderr
        dispatch_id = _parse_dispatch_id(r.stdout + r.stderr)
        state_file = repo / ".frob" / "dispatch" / f"{dispatch_id}.json"
        assert state_file.exists(), f"state file not found: {state_file}"

    def test_multiple_creates_give_unique_ids(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r1 = run("dispatch", "create", "alpha", cwd=repo)
        r2 = run("dispatch", "create", "beta", cwd=repo)
        assert r1.returncode == 0 and r2.returncode == 0
        id1 = _parse_dispatch_id(r1.stdout + r1.stderr)
        id2 = _parse_dispatch_id(r2.stdout + r2.stderr)
        assert id1 != id2

        # Cleanup
        run("dispatch", "abort", id1, cwd=repo)
        run("dispatch", "abort", id2, cwd=repo)

    def test_create_outside_git_repo_fails(self, tmp_path):
        r = run("dispatch", "create", "label", cwd=tmp_path)
        assert r.returncode != 0


class TestDispatchList:
    def test_list_empty(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "list", cwd=repo)
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "no active" in out.lower() or out.strip() == "" or "0" in out

    def test_list_shows_created(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "my-task", cwd=repo)
        dispatch_id = _parse_dispatch_id(r.stdout + r.stderr)

        r = run("dispatch", "list", cwd=repo)
        assert r.returncode == 0
        assert dispatch_id in (r.stdout + r.stderr)

        run("dispatch", "abort", dispatch_id, cwd=repo)

    def test_list_shows_label(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "fancy-label", cwd=repo)
        dispatch_id = _parse_dispatch_id(r.stdout + r.stderr)

        r = run("dispatch", "list", cwd=repo)
        assert "fancy-label" in (r.stdout + r.stderr)

        run("dispatch", "abort", dispatch_id, cwd=repo)

    def test_list_multiple(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r1 = run("dispatch", "create", "task-a", cwd=repo)
        r2 = run("dispatch", "create", "task-b", cwd=repo)
        id1 = _parse_dispatch_id(r1.stdout + r1.stderr)
        id2 = _parse_dispatch_id(r2.stdout + r2.stderr)

        r = run("dispatch", "list", cwd=repo)
        out = r.stdout + r.stderr
        assert id1 in out
        assert id2 in out

        run("dispatch", "abort", id1, cwd=repo)
        run("dispatch", "abort", id2, cwd=repo)


class TestDispatchAbort:
    def test_abort_removes_state_file(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "to-abort", cwd=repo)
        dispatch_id = _parse_dispatch_id(r.stdout + r.stderr)
        state_file = repo / ".frob" / "dispatch" / f"{dispatch_id}.json"
        assert state_file.exists()

        r = run("dispatch", "abort", dispatch_id, cwd=repo)
        assert r.returncode == 0, r.stderr
        assert not state_file.exists()

    def test_abort_removes_worktree(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "to-abort", cwd=repo)
        dispatch_id = _parse_dispatch_id(r.stdout + r.stderr)

        wt_path = None
        for line in (r.stdout + r.stderr).splitlines():
            if "worktree:" in line:
                wt_path = Path(line.split("worktree:")[1].strip())

        run("dispatch", "abort", dispatch_id, cwd=repo)
        if wt_path:
            assert not wt_path.exists()

    def test_abort_gone_from_list(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "create", "ephemeral", cwd=repo)
        dispatch_id = _parse_dispatch_id(r.stdout + r.stderr)

        run("dispatch", "abort", dispatch_id, cwd=repo)

        r = run("dispatch", "list", cwd=repo)
        assert dispatch_id not in (r.stdout + r.stderr)

    def test_abort_unknown_id_fails(self, tmp_path):
        repo = _setup_repo(tmp_path)
        r = run("dispatch", "abort", "nonexistent-id-abc123", cwd=repo)
        assert r.returncode != 0
