"""T-1400 branch-gap closure for `frob.app.clean_runner.run`.

`tests/unit/test_app_runners_t0875_leaf_collision.py::TestCleanRunnerRun`
already covers the dry-run-nothing-to-clean and `--json` branches. This
file targets the two branches that suite never reaches: `clean()`
returning `Err` (`sys.exit(1)`), and the executed (`-y`/`--yes`) path over
a tree with real entries to remove -- distinct from the JSON and
"nothing to clean" branches already covered.
"""
# frob:waive DEPR005 reason="resolver name-collision, not real adoption: this file's run() calls target frob.app.clean_runner.run directly; the deprecated xref/outline/map runner run symbols share only the bare name (same class as tests/system/test_cli_sys_audit.py's waived precedent)"  # noqa: E501

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.app.clean_runner import run as clean_run
from frob.app.config import AppConfig


def _git(root: Path, *args: str) -> None:
    """Run a `git` subcommand quietly against `root`, raising on failure."""
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """A minimal initialized-and-committed git repo with one stray
    untracked artifact file (`__pycache__`) so `clean()` has something
    real to report/remove, unlike the empty-tree fixture the sibling
    suite uses."""
    root = tmp_path / "proj"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    (root / "src.py").write_text("x = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    cache_dir = root / "__pycache__"
    cache_dir.mkdir()
    (cache_dir / "src.cpython-311.pyc").write_bytes(b"\x00" * 16)
    return root


class TestCleanRunnerRunErrPath:
    """The `result.is_err` branch: `clean()` failing with `sys.exit(1)`."""

    def test_not_a_repo_exits_1(self, tmp_path: Path) -> None:
        """A root with no `.git` at all is `CleanError.NotARepo`, and
        `run` exits 1 rather than rendering a report."""
        cfg = AppConfig(clean_path=tmp_path, clean_yes=False, clean_json=False)
        with pytest.raises(SystemExit) as exc_info:
            clean_run(cfg)
        assert exc_info.value.code == 1


class TestCleanRunnerRunExecuted:
    """The `executed=True` (`-y`/`--yes`) rendering branch, distinct from
    the dry-run and JSON paths the sibling suite already covers."""

    def test_yes_flag_removes_and_reports_removed(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`--yes` actually removes the stray `__pycache__` artifact and
        the report renders `removed`, not `would remove`."""
        cfg = AppConfig(clean_path=git_repo, clean_yes=True, clean_json=False)
        clean_run(cfg)
        out = capsys.readouterr().out
        assert "removed" in out
        assert "would remove" not in out
        assert "dry-run only" not in out
        assert not (git_repo / "__pycache__").exists()

    def test_dry_run_with_entries_shows_would_remove_hint(
        self, git_repo: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """A dry run over a tree with real entries prints the `would
        remove` verb plus the trailing dry-run hint line -- the
        `not cfg.clean_yes and report.entries` branch, absent from the
        empty-tree dry-run case."""
        cfg = AppConfig(clean_path=git_repo, clean_yes=False, clean_json=False)
        clean_run(cfg)
        out = capsys.readouterr().out
        assert "would remove" in out
        assert "dry-run only" in out
        assert (git_repo / "__pycache__").exists()
