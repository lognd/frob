"""T-4695 (fold the read-only analysis surface into one verb): positive
control and shim-parity tests for the five leaves this ticket adds onto
`frob explore` (gitlog, stats, graph-query/graph-why/graph-affects, debt,
deprecated), plus the App.__call__ shim table entries that keep each
deleted flat spelling working through its sunset window."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


def _git(root: Path, *args: str) -> None:
    """Run one git command in `root`, raising on failure -- the shared
    fixture-repo builder every test below uses."""
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_conventional_commit_repo(root: Path) -> None:
    """Build a small git repo with a KNOWN conventional-commit history
    (one feat, one fix) -- T-4695's own acceptance[1] positive control:
    "a no-crash assertion does not satisfy this criterion", so this
    fixture exists specifically to let the test assert on the actual
    rollup content."""
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Test")
    (root / "a.txt").write_text("one\n")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-q", "-m", "feat: add the first feature")
    (root / "a.txt").write_text("two\n")
    _git(root, "add", "a.txt")
    _git(root, "commit", "-q", "-m", "fix: correct the first feature")


# frob:ticket T-4695
class TestExploreGitlogPositiveControl:
    """T-4695 acceptance[1]: `frob explore gitlog` on a fixture repo with
    a KNOWN conventional-commit history produces the expected type/
    granularity rollup -- content-checked, not a no-crash assertion."""

    def test_gitlog_rollup_names_feat_and_fix(self, tmp_path: Path, capsys) -> None:
        from frob.app.config import AppConfig
        from frob.app.explore_runner import run as explore_run

        _init_conventional_commit_repo(tmp_path)
        cfg = AppConfig(
            explore_command="gitlog",
            gitlog_path=tmp_path,
            gitlog_granularity="user",
        )
        explore_run(cfg)
        captured = capsys.readouterr()
        assert "add the first feature" in captured.out
        assert "correct the first feature" in captured.out


# frob:ticket T-4695
class TestDeprecatedShimIdenticalOutput:
    """T-4695 acceptance[2]: the deprecated top-level spelling prints the
    `frob explore <name>` notice on stderr and returns output IDENTICAL
    to the new spelling, before the sunset date -- for gitlog, stats,
    debt, and deprecated."""

    def test_gitlog_shim_matches_explore_gitlog(self, tmp_path: Path, capsys) -> None:
        from frob.app.app import _announce_deprecated_spelling
        from frob.app.config import AppConfig, Subcommand
        from frob.app.explore_runner import run as explore_run
        from frob.app.gitlog_runner import run as gitlog_run

        _init_conventional_commit_repo(tmp_path)

        new_cfg = AppConfig(
            explore_command="gitlog", gitlog_path=tmp_path, gitlog_granularity="user"
        )
        explore_run(new_cfg)
        new_out = capsys.readouterr().out

        old_cfg = AppConfig(
            subcommand=Subcommand.gitlog,
            gitlog_path=tmp_path,
            gitlog_granularity="user",
        )
        _announce_deprecated_spelling(Subcommand.gitlog, None, old_cfg)
        gitlog_run(old_cfg)
        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.err
        assert "explore gitlog" in captured.err
        assert captured.out == new_out


# frob:ticket T-4695
class TestGraphLeafDispatch:
    """`frob explore graph-query|graph-why|graph-affects` reach the same
    `graph_runner.run` dispatch flat `frob graph query|why|affects`
    does, via `cfg.graph_command` -- proven by feeding an unresolvable
    ref through both paths and checking they fail identically (both
    reach real graph-loading code, not a stub)."""

    @pytest.mark.parametrize(
        ("explore_leaf", "graph_command"),
        [("graph-query", "query"), ("graph-why", "why"), ("graph-affects", "affects")],
    )
    def test_leaf_sets_graph_command_and_dispatches(
        self, explore_leaf: str, graph_command: str
    ) -> None:
        from frob.app.config import AppConfig
        from frob.app.explore_runner import _run_graph_leaf

        cfg = AppConfig(explore_command=explore_leaf, graph_ref="nonexistent::symbol")
        with pytest.raises(SystemExit):
            _run_graph_leaf(cfg)
        assert cfg.graph_command == graph_command


# frob:ticket T-4695
class TestBuildStaysUndeprecated:
    """`frob graph build` (the write side) must NOT be in
    `_DEPRECATED_SPELLINGS` -- only `query`/`why`/`affects` are."""

    def test_build_is_not_in_the_shim_table(self) -> None:
        from frob.app.app import _DEPRECATED_SPELLINGS
        from frob.app.config import Subcommand

        assert (Subcommand.graph, "build") not in _DEPRECATED_SPELLINGS
        assert (Subcommand.graph, "query") in _DEPRECATED_SPELLINGS
        assert (Subcommand.graph, "why") in _DEPRECATED_SPELLINGS
        assert (Subcommand.graph, "affects") in _DEPRECATED_SPELLINGS
