"""
Integration tests: frob dispatch + frob edit --stage compose correctly.

Verifies that:
- Patches staged inside a dispatch worktree are scoped to that worktree.
- edit --commit applies correctly inside the worktree.
- dispatch collect lands the change on the main branch.
- The main repo's files and patch dirs are unaffected until collect.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

FROB = [sys.executable, "-m", "frob"]

PY_SRC = """\
def alpha(x: int) -> int:
    return x + 1


def beta(y: str) -> str:
    return y.upper()
"""


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )


def _frob(
    args: list[str], cwd: Path | None = None, input: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        FROB + args,
        capture_output=True,
        text=True,
        input=input,
        cwd=str(cwd) if cwd else None,
    )


def _setup_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create a git repo with one committed Python file. Returns (repo, src_file)."""
    repo = tmp_path / "repo"
    repo.mkdir()

    _git(["init", "-b", "main"], repo)
    _git(["config", "user.email", "test@test.com"], repo)
    _git(["config", "user.name", "Test"], repo)

    # Need a pyproject.toml so frob find_project_root anchors here
    (repo / "pyproject.toml").write_text('[project]\nname = "test"\n')

    src = repo / "src"
    src.mkdir()
    py_file = src / "mod.py"
    py_file.write_text(PY_SRC)

    _git(["add", "."], repo)
    _git(["commit", "-m", "init: initial commit"], repo)

    return repo, py_file


class TestDispatchEditIntegration:
    def test_patch_scoped_to_worktree(self, tmp_path):
        """Staging inside a dispatch worktree does not affect the main repo."""
        repo, py_file = _setup_repo(tmp_path)

        # Create a dispatch worktree
        r_dispatch = _frob(["dispatch", "create", "fix-alpha"], cwd=repo)
        assert r_dispatch.returncode == 0, r_dispatch.stderr
        wt_path, _ = _parse_dispatch(r_dispatch.stdout)
        assert wt_path.exists(), f"worktree not found: {wt_path}"

        wt_py_file = wt_path / "src" / "mod.py"
        assert wt_py_file.exists()

        # Stage a patch INSIDE the worktree
        new_src = "def alpha(x: int) -> int:\n    return x * 99\n"
        r = _frob(
            ["edit", str(wt_py_file), "alpha", "--stage"], cwd=wt_path, input=new_src
        )
        assert r.returncode == 0, r.stderr

        # Patch file must be inside worktree, not main repo
        main_frob_edits = repo / ".frob" / "edits"
        assert not main_frob_edits.exists(), "patch leaked into main repo's .frob/edits"
        wt_frob_edits = wt_path / ".frob" / "edits"
        assert wt_frob_edits.exists(), "patch not found inside worktree"

        # Main repo file is unchanged
        assert "return x + 1" in py_file.read_text()

        # Cleanup
        _, did = _parse_dispatch(r_dispatch.stdout)
        _frob(["dispatch", "abort", did], cwd=repo)

    def test_commit_inside_worktree_applies_to_worktree_file(self, tmp_path):
        """edit --commit inside worktree modifies the worktree's copy, not main."""
        repo, py_file = _setup_repo(tmp_path)

        r = _frob(["dispatch", "create", "fix-beta"], cwd=repo)
        assert r.returncode == 0, r.stderr
        wt_path, dispatch_id = _parse_dispatch(r.stdout)

        wt_py_file = wt_path / "src" / "mod.py"
        new_src = "def beta(y: str) -> str:\n    return y.lower()\n"

        _frob(["edit", str(wt_py_file), "beta", "--stage"], cwd=wt_path, input=new_src)
        r = _frob(["edit", str(wt_py_file), "--commit"], cwd=wt_path)
        assert r.returncode == 0, r.stderr

        # Worktree file changed
        assert "return y.lower()" in wt_py_file.read_text()
        # Worktree preserves other function
        assert "def alpha" in wt_py_file.read_text()

        # Main repo file UNCHANGED
        assert "return y.upper()" in py_file.read_text()

        _frob(["dispatch", "abort", dispatch_id], cwd=repo)

    def test_collect_lands_change_on_main(self, tmp_path):
        """Full round-trip: stage -> commit inside worktree -> dispatch collect -> main updated."""
        repo, py_file = _setup_repo(tmp_path)

        r = _frob(["dispatch", "create", "update-alpha"], cwd=repo)
        assert r.returncode == 0, r.stderr
        wt_path, dispatch_id = _parse_dispatch(r.stdout)

        wt_py_file = wt_path / "src" / "mod.py"
        new_src = "def alpha(x: int) -> int:\n    return x * 7\n"

        _frob(["edit", str(wt_py_file), "alpha", "--stage"], cwd=wt_path, input=new_src)
        _frob(["edit", str(wt_py_file), "--commit"], cwd=wt_path)

        # Agent makes a git commit inside the worktree
        _git(["add", "src/mod.py"], wt_path)
        _git(["commit", "-m", "feat: multiply alpha by 7"], wt_path)

        # Collect: rebase + ff-merge onto main
        r = _frob(["dispatch", "collect", dispatch_id], cwd=repo)
        assert r.returncode == 0, f"collect failed: {r.stderr}"

        # Main repo file now has the change
        assert "return x * 7" in py_file.read_text()
        # Other function intact
        assert "def beta" in py_file.read_text()

    def test_two_agents_same_file_no_collision(self, tmp_path):
        """Two agents in separate worktrees stage different functions; both land correctly."""
        repo, py_file = _setup_repo(tmp_path)

        # Two dispatches
        r1 = _frob(["dispatch", "create", "agent-alpha"], cwd=repo)
        r2 = _frob(["dispatch", "create", "agent-beta"], cwd=repo)
        assert r1.returncode == 0 and r2.returncode == 0

        wt1, d1 = _parse_dispatch(r1.stdout)
        wt2, d2 = _parse_dispatch(r2.stdout)

        # Agent 1 edits alpha inside wt1
        new_alpha = "def alpha(x: int) -> int:\n    return x + 100\n"
        _frob(
            ["edit", str(wt1 / "src" / "mod.py"), "alpha", "--stage"],
            cwd=wt1,
            input=new_alpha,
        )
        _frob(["edit", str(wt1 / "src" / "mod.py"), "--commit"], cwd=wt1)
        _git(["add", "src/mod.py"], wt1)
        _git(["commit", "-m", "feat: alpha +100"], wt1)

        # Agent 2 edits beta inside wt2
        new_beta = "def beta(y: str) -> str:\n    return y.strip()\n"
        _frob(
            ["edit", str(wt2 / "src" / "mod.py"), "beta", "--stage"],
            cwd=wt2,
            input=new_beta,
        )
        _frob(["edit", str(wt2 / "src" / "mod.py"), "--commit"], cwd=wt2)
        _git(["add", "src/mod.py"], wt2)
        _git(["commit", "-m", "feat: beta strip"], wt2)

        # Collect both (sequential)
        r = _frob(["dispatch", "collect", d1], cwd=repo)
        assert r.returncode == 0, f"collect d1 failed: {r.stderr}"
        r = _frob(["dispatch", "collect", d2], cwd=repo)
        assert r.returncode == 0, f"collect d2 failed: {r.stderr}"

        content = py_file.read_text()
        assert "return x + 100" in content, "alpha change missing"
        assert "return y.strip()" in content, "beta change missing"


def _parse_dispatch(output: str) -> tuple[Path, str]:
    """Extract (worktree_path, dispatch_id) from dispatch create output."""
    dispatch_id = None
    wt_path = None
    for line in output.splitlines():
        if line.startswith("dispatch "):
            dispatch_id = line.split()[1]
        if "worktree:" in line:
            wt_path = Path(line.split("worktree:")[1].strip())
    assert dispatch_id and wt_path, f"could not parse dispatch output: {output!r}"
    return wt_path, dispatch_id


def _dispatch_id(r: subprocess.CompletedProcess, repo: Path) -> str:
    _, did = _parse_dispatch(r.stdout)
    return did
