"""End-to-end tests for `frob test` (docs/modules/testing.md)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _init_repo_with_bound_test(tmp_path: Path) -> Path:
    _git("init", "-q", cwd=tmp_path)
    _git("config", "user.email", "test@example.com", cwd=tmp_path)
    _git("config", "user.name", "Test", cwd=tmp_path)

    (tmp_path / "pkg.py").write_text(
        "def add(x: int, y: int) -> int:\n    return x + y\n"
    )
    (tmp_path / "test_pkg.py").write_text(
        "from pkg import add\n\n"
        "def test_add() -> None:\n"
        "    # frob:tests pkg.py::add\n"
        "    assert add(1, 2) == 3\n"
    )
    (tmp_path / "frob.toml").write_text(
        "[[test.runner]]\n"
        'language = "python"\n'
        'command = ["python", "-m", "pytest", "-q", "{ids}"]\n'
        'all_command = ["python", "-m", "pytest", "-q"]\n'
        'cwd = "."\n'
    )
    _git("add", "-A", cwd=tmp_path)
    _git("commit", "-q", "-m", "init", cwd=tmp_path)
    return tmp_path


class TestFrobTest:
    def test_all_runs_full_suite(self, tmp_path):
        root = _init_repo_with_bound_test(tmp_path)
        r = run("test", str(root), "--all")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out

    def test_selects_bound_test_for_touched_symbol(self, tmp_path):
        root = _init_repo_with_bound_test(tmp_path)
        # Touch the bound symbol's body (keep signature stable) after the
        # initial commit so the working diff has something to select against.
        (root / "pkg.py").write_text(
            "def add(x: int, y: int) -> int:\n    result = x + y\n    return result\n"
        )
        r = run("test", str(root), "--base", "HEAD")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
