"""Tests for T-0484's touched-set coverage helper
(frob.testing._incremental_coverage.python_coverage_targets) and T-0538's
natives-clobber guard on the `make coverage`/`make coverage-fast` targets."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path

from frob.graph import build_graph
from frob.testing import python_coverage_targets

#: T-0538: repo root, resolved the same way every other Makefile-adjacent
#: test in this repo would -- two levels up from this test file
#: (tests/test_coverage.py -> repo root).
_REPO_ROOT = Path(__file__).resolve().parent.parent


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
    # T-1006: a real repo always gitignores .frob/ (frob's own scratch
    # state); without this a fixture with no .gitignore lets frob's own
    # derived.lock/cache.db writes (produced merely by calling build_graph
    # during the test itself) show up as untouched-by-user files in
    # `git ls-files --others`, which python_coverage_targets then treats
    # as a genuine unknown-language touched file and falls back to a
    # suite-wide '*' selection -- not a real product bug, just an
    # under-configured fixture repo.
    (root / ".gitignore").write_text(".frob/\n", encoding="utf-8")


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


class TestCoverageTargetNativesGuard:
    """T-0538: `make coverage`/`make coverage-fast` both depend on
    `$(STAMP)` (`uv sync`), which silently removes the editable
    `strata_core`/`frob_core` natives `make core` installed -- neither is a
    declared dependency `uv sync` knows to preserve. This dry-runs the real
    Makefile (`make -n`, which never executes a single recipe line) and
    asserts the restore-then-verify guard (`make core` then `frob doctor`)
    appears BEFORE the pytest invocation in both targets' expanded recipe,
    so a regression that reorders or drops the guard fails this test
    without ever running the (slow, `make coverage`-forbidden per the
    playbook's 6b) real recipe."""

    def _dry_run(self, target: str) -> str:
        """`make -n <target>` output: the exact shell commands `make` WOULD
        run, in order, with none of them actually executed -- safe to call
        from a test."""
        result = subprocess.run(
            ["make", "-n", target],
            cwd=_REPO_ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout

    def _assert_guard_precedes_pytest(self, output: str) -> None:
        """`make core` and `frob doctor` must both appear, in that relative
        order, strictly before the first `pytest --cov` invocation -- the
        exact ordering that fails loudly on a missing native instead of
        letting pytest collection blow up mid-suite (the T-0538 incident)."""
        core_idx = output.index("make core")
        doctor_idx = output.index("frob doctor")
        pytest_idx = output.index("pytest --cov")
        assert core_idx < doctor_idx < pytest_idx, (
            f"expected 'make core' < 'frob doctor' < 'pytest --cov', "
            f"got indices {core_idx}, {doctor_idx}, {pytest_idx} in:\n{output}"
        )

    def test_coverage_target_restores_and_verifies_natives_before_pytest(
        self,
    ) -> None:
        """`make coverage`'s dry-run recipe restores natives (`make core`)
        and verifies them (`frob doctor`) before the coverage pytest run."""
        self._assert_guard_precedes_pytest(self._dry_run("coverage"))

    def test_coverage_fast_incremental_branch_restores_and_verifies_natives(
        self,
    ) -> None:
        """`make coverage-fast`'s incremental branch (the one that does NOT
        fall back to `make coverage`) is subject to the exact same
        `$(STAMP)`/`uv sync` clobber hazard, since it also depends on
        `$(STAMP)` -- this asserts its own `make core && frob doctor`
        guard is present in the dry-run output before its own pytest
        invocation."""
        self._assert_guard_precedes_pytest(self._dry_run("coverage-fast"))
