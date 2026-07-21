"""Tests for T-0484's touched-set coverage helper
(frob.testing._incremental_coverage.python_coverage_targets)."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from frob.graph import build_graph
from frob.testing import python_coverage_targets


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))
    return path


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
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


class TestPythonCoverageTargets:
    def test_touched_source_selects_test(self, tmp_path: Path) -> None:
        """T-0484: a source file changed since `base` selects the test bound
        to it via `frob:tests`, mirroring `frob test --base`'s own touched-
        set selection (the shared, already-trusted algorithm) -- the
        touched-set coverage recipe's whole premise."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_foo.py",
            """
            def test_widget() -> None:
                # frob:tests src/foo.py::widget
                pass
            """,
        )
        _commit(tmp_path, "base")

        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 2
            """,
        )
        snapshot = build_graph(tmp_path, tmp_path.parent / "cache.db").danger_ok
        targets = python_coverage_targets(tmp_path, snapshot, "main")
        assert any("test_widget" in t for t in targets)

    def test_nothing_touched_returns_empty(self, tmp_path: Path) -> None:
        """T-0484: an unchanged tree (no diff against `base`) selects nothing
        -- callers treat this as "no incremental re-measurement needed," not
        an error."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _write(
            tmp_path,
            "tests/test_foo.py",
            """
            def test_widget() -> None:
                # frob:tests src/foo.py::widget
                pass
            """,
        )
        _commit(tmp_path, "base")
        snapshot = build_graph(tmp_path, tmp_path.parent / "cache.db").danger_ok
        targets = python_coverage_targets(tmp_path, snapshot, "main")
        assert targets == ()

    def test_bad_base_ref_returns_empty(self, tmp_path: Path) -> None:
        """T-0484: a `working_diff` failure (e.g. an unknown base ref) degrades
        to an empty result rather than propagating an exception -- the
        Makefile recipe calling this must be able to fall back to a full
        `make coverage` run instead of crashing."""
        _init_repo(tmp_path)
        _write(
            tmp_path,
            "src/foo.py",
            """
            def widget() -> int:
                return 1
            """,
        )
        _commit(tmp_path, "base")
        snapshot = build_graph(tmp_path, tmp_path.parent / "cache.db").danger_ok
        targets = python_coverage_targets(tmp_path, snapshot, "no-such-ref")
        assert targets == ()
