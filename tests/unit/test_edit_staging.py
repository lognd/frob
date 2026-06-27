"""Unit tests for frob.edit staging model."""

import time
from pathlib import Path

import pytest

from frob.edit import (
    EditError,
    commit,
    isolate,
    replace,
    stage,
    status,
)

PY_SRC = """\
def foo(x: int) -> int:
    return x + 1


def bar(y: str) -> str:
    return y.upper()


class MyClass:
    def method(self) -> None:
        pass

    def other(self) -> int:
        return 0
"""


def _py(tmp_path: Path) -> Path:
    p = tmp_path / "mod.py"
    p.write_text(PY_SRC)
    return p


class TestStage:
    def test_stage_creates_patch_file(self, tmp_path):
        p = _py(tmp_path)
        result = stage(p, "foo", "def foo(x): return x * 2\n", project_root=tmp_path)
        assert result.is_ok
        patch_file = result.danger_ok
        assert patch_file.exists()
        assert patch_file.suffix == ".patch"

    def test_stage_does_not_modify_source(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x): return 999\n", project_root=tmp_path)
        assert "return x + 1" in p.read_text()

    def test_stage_overwrites_same_symbol(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x): return 1\n", project_root=tmp_path)
        time.sleep(0.01)
        stage(p, "foo", "def foo(x): return 2\n", project_root=tmp_path)
        patches = status(p, project_root=tmp_path)
        assert len(patches) == 1
        assert "return 2" in patches[0].new_source

    def test_status_shows_pending(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x): return 1\n", project_root=tmp_path)
        stage(p, "bar", "def bar(y): return y\n", project_root=tmp_path)
        patches = status(p, project_root=tmp_path)
        symbols = {pa.symbol for pa in patches}
        assert symbols == {"foo", "bar"}

    def test_unsupported_file_is_err(self, tmp_path):
        p = tmp_path / "file.txt"
        p.write_text("hello")
        result = stage(p, "foo", "x", project_root=tmp_path)
        assert result.is_err
        assert result.danger_err == EditError.UnsupportedFile


class TestCommit:
    def test_commit_applies_single_patch(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x: int) -> int:\n    return x * 99\n", project_root=tmp_path)
        result = commit(p, project_root=tmp_path)
        assert result.is_ok
        assert "return x * 99" in p.read_text()

    def test_commit_preserves_other_symbols(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x: int) -> int:\n    return 0\n", project_root=tmp_path)
        commit(p, project_root=tmp_path)
        content = p.read_text()
        assert "def bar" in content
        assert "class MyClass" in content

    def test_commit_applies_multiple_patches(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x: int) -> int:\n    return -1\n", project_root=tmp_path)
        stage(p, "bar", "def bar(y: str) -> str:\n    return y.lower()\n", project_root=tmp_path)
        result = commit(p, project_root=tmp_path)
        assert result.is_ok
        content = p.read_text()
        assert "return -1" in content
        assert "return y.lower()" in content

    def test_commit_clears_patches(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x): return 0\n", project_root=tmp_path)
        commit(p, project_root=tmp_path)
        assert status(p, project_root=tmp_path) == []

    def test_commit_nothing_to_commit(self, tmp_path):
        p = _py(tmp_path)
        result = commit(p, project_root=tmp_path)
        assert result.is_err
        assert result.danger_err == EditError.NothingToCommit

    def test_commit_resolves_duplicate_symbol_keeps_newest(self, tmp_path):
        p = _py(tmp_path)
        stage(p, "foo", "def foo(x): return 1\n", project_root=tmp_path)
        time.sleep(0.02)
        # Overwrite staged patch with a newer version
        stage(p, "foo", "def foo(x): return 2\n", project_root=tmp_path)
        result = commit(p, project_root=tmp_path)
        assert result.is_ok
        assert "return 2" in p.read_text()

    def test_concurrent_agents_no_overwrite(self, tmp_path):
        """Two agents stage different symbols; commit applies both correctly."""
        p = _py(tmp_path)
        # Simulate agent A staging foo, agent B staging bar concurrently
        stage(p, "foo", "def foo(x: int) -> int:\n    return 10\n", project_root=tmp_path)
        stage(p, "bar", "def bar(y: str) -> str:\n    return 'fixed'\n", project_root=tmp_path)
        result = commit(p, project_root=tmp_path)
        assert result.is_ok
        content = p.read_text()
        assert "return 10" in content
        assert "return 'fixed'" in content
        # Unrelated symbols must be intact
        assert "class MyClass" in content
        assert "def method" in content

    def test_method_patch(self, tmp_path):
        p = _py(tmp_path)
        new_method = "    def method(self) -> None:\n        print('patched')\n"
        stage(p, "MyClass.method", new_method, project_root=tmp_path)
        result = commit(p, project_root=tmp_path)
        assert result.is_ok
        assert "print('patched')" in p.read_text()
        assert "def other" in p.read_text()


class TestWorktreeIsolation:
    """Patches staged inside a simulated dispatch worktree stay isolated there."""

    def test_patch_dir_scoped_to_worktree_root(self, tmp_path):
        # Simulate a linked git worktree: .git is a FILE (not a dir) at root
        from frob.edit import _find_project_root, _patch_dir

        worktree_root = tmp_path / "worktree_a"
        worktree_root.mkdir()
        (worktree_root / ".git").write_text("gitdir: /repo/.git/worktrees/worktree_a\n")

        src_dir = worktree_root / "src" / "frob" / "mod"
        src_dir.mkdir(parents=True)
        py_file = src_dir / "impl.py"
        py_file.write_text("def fn(): pass\n")

        root = _find_project_root(py_file)
        assert root == worktree_root, f"expected worktree root, got {root}"

        patch_dir = _patch_dir(py_file, None)
        assert str(patch_dir).startswith(str(worktree_root)), (
            f"patch dir {patch_dir} escaped the worktree {worktree_root}"
        )

    def test_two_worktrees_dont_share_patch_dirs(self, tmp_path):
        from frob.edit import _patch_dir

        for wt in ("a", "b"):
            root = tmp_path / f"worktree_{wt}"
            root.mkdir()
            (root / ".git").write_text(f"gitdir: /repo/.git/worktrees/{wt}\n")
            src = root / "src"
            src.mkdir()
            (src / "mod.py").write_text("def fn(): pass\n")

        pa = _patch_dir(tmp_path / "worktree_a" / "src" / "mod.py", None)
        pb = _patch_dir(tmp_path / "worktree_b" / "src" / "mod.py", None)
        assert pa != pb, "worktrees must not share patch directories"
        assert str(pa).startswith(str(tmp_path / "worktree_a"))
        assert str(pb).startswith(str(tmp_path / "worktree_b"))

    def test_stage_and_commit_inside_simulated_worktree(self, tmp_path):
        # Full round-trip: stage inside a worktree, commit stays local
        worktree_root = tmp_path / "worktree"
        worktree_root.mkdir()
        (worktree_root / ".git").write_text("gitdir: /fake/.git/worktrees/wt\n")

        src = worktree_root / "src"
        src.mkdir()
        py_file = src / "mod.py"
        py_file.write_text(PY_SRC)

        stage(py_file, "foo", "def foo(x: int) -> int:\n    return 42\n")
        patches = status(py_file)
        assert len(patches) == 1
        assert patches[0].symbol == "foo"

        result = commit(py_file)
        assert result.is_ok
        assert "return 42" in py_file.read_text()

        # Patch dir must be inside the worktree, not tmp_path root
        from frob.edit import _patch_dir
        patch_dir = _patch_dir(py_file, None)
        assert str(patch_dir).startswith(str(worktree_root))


class TestImmediateReplace:
    """replace() is still safe for single-agent use (lock + atomic write)."""

    def test_replace_works(self, tmp_path):
        p = _py(tmp_path)
        result = replace(p, "foo", "def foo(x: int) -> int:\n    return 0\n")
        assert result.is_ok
        assert "return 0" in p.read_text()

    def test_replace_preserves_others(self, tmp_path):
        p = _py(tmp_path)
        replace(p, "foo", "def foo(x: int) -> int:\n    return 0\n")
        assert "def bar" in p.read_text()
