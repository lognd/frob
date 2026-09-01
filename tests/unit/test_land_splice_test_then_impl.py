"""T-3546: `frob.tickets._land_splice.classify_test_then_impl_paths`/
`compose_test_then_impl_commits` -- the UNWIRED mechanical primitives for
the tests-first-then-implementation land splice design
(`docs/design/land-splice-test-then-impl.md`). Proven against a scratch
git repo, never the live root, same posture as
`tests/unit/test_land_compose.py`. Neither function has a caller in the
live land path yet -- this is proving the primitive in isolation, per
the design doc's Rollout plan."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from frob.tickets._land_splice import (
    classify_test_then_impl_paths,
    compose_test_then_impl_commits,
)


def _run(argv: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run a git command in `cwd`, asserting success -- test-only helper."""
    return subprocess.run(
        argv, cwd=str(cwd), check=True, capture_output=True, text=True
    )


class TestClassifyTestThenImplPaths:
    """Mechanical, path-based, no-guessing classification -- `None` is the
    only "no clean split" signal, never a fabricated split."""

    def test_mixed_paths_split_into_two_groups(self) -> None:
        # frob:tests \
        # tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths.\
        # test_mixed_paths_split_into_two_groups
        result = classify_test_then_impl_paths(
            [
                "src/frob/widget.py",
                "tests/test_widget.py",
                "tests/unit/test_widget_helper.py",
                "docs/modules/widget.md",
            ]
        )
        assert result is not None
        test_paths, impl_paths = result
        assert test_paths == (
            "tests/test_widget.py",
            "tests/unit/test_widget_helper.py",
        )
        assert impl_paths == ("docs/modules/widget.md", "src/frob/widget.py")

    def test_no_test_paths_returns_none(self) -> None:
        # frob:tests \
        # tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths.\
        # test_no_test_paths_returns_none
        result = classify_test_then_impl_paths(
            ["src/frob/widget.py", "docs/modules/widget.md"]
        )
        assert result is None

    def test_no_impl_paths_returns_none(self) -> None:
        # frob:tests \
        # tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths.\
        # test_no_impl_paths_returns_none
        result = classify_test_then_impl_paths(["tests/test_widget.py"])
        assert result is None

    def test_underscore_test_suffix_file_outside_tests_dir_still_classified(
        self,
    ) -> None:
        """A `*_test.py`/`test_*` file outside `tests/**` (rare in this
        repo's own style, but the heuristic this mirrors -- `frob.gates.
        _is_test_path` -- covers it) still classifies as TEST, matching
        that shared convention exactly."""
        # frob:tests \
        # tests/unit/test_land_splice_test_then_impl.py::TestClassifyTestThenImplPaths.\
        # test_underscore_test_suffix_file_outside_tests_dir_still_classified
        result = classify_test_then_impl_paths(
            ["scripts/widget_test.py", "src/frob/widget.py"]
        )
        assert result is not None
        test_paths, impl_paths = result
        assert test_paths == ("scripts/widget_test.py",)
        assert impl_paths == ("src/frob/widget.py",)


@pytest.fixture
def scratch_repo(tmp_path: Path) -> Path:
    """A minimal git repo: `main` has one base file; `feature` adds both a
    test file and an implementation file relative to `main` -- the mixed
    changeset `compose_test_then_impl_commits` splits."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _run(["git", "init", "-q", "-b", "main"], repo)
    _run(["git", "config", "user.email", "test@example.com"], repo)
    _run(["git", "config", "user.name", "Test"], repo)
    (repo / ".gitignore").write_text(".frob/\n")
    _run(["git", "add", ".gitignore"], repo)
    _run(["git", "commit", "-q", "-m", "gitignore .frob/"], repo)
    (repo / "a.txt").write_text("base\n")
    _run(["git", "add", "a.txt"], repo)
    _run(["git", "commit", "-q", "-m", "base"], repo)

    _run(["git", "checkout", "-q", "-b", "feature"], repo)
    (repo / "tests").mkdir()
    (repo / "tests" / "test_widget.py").write_text("def test_widget(): ...\n")
    (repo / "widget.py").write_text("def widget(): ...\n")
    _run(["git", "add", "tests/test_widget.py", "widget.py"], repo)
    _run(["git", "commit", "-q", "-m", "add widget + test"], repo)
    _run(["git", "checkout", "-q", "main"], repo)
    return repo


class TestComposeTestThenImplCommits:
    """`compose_test_then_impl_commits` composes a test-only commit
    parented on `pre_land_tip`, then an impl-only commit parented on
    THAT commit -- neither step touches the checked-out working tree."""

    def test_two_commits_chain_correctly(self, scratch_repo: Path) -> None:
        """Given a scratch repo with a mixed test+impl feature branch,
        when compose_test_then_impl_commits runs, then commit 1 contains
        ONLY the test file, commit 2 (parented on commit 1) additionally
        contains the impl file, and the working tree is never touched."""
        # frob:tests \
        # tests/unit/test_land_splice_test_then_impl.py::TestComposeTestThenImplCommits\
        # .test_two_commits_chain_correctly
        a_path = scratch_repo / "a.txt"
        before_mtime = a_path.stat().st_mtime_ns

        base = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        feature = _run(["git", "rev-parse", "feature"], scratch_repo).stdout.strip()

        split = classify_test_then_impl_paths(["tests/test_widget.py", "widget.py"])
        assert split is not None
        test_paths, impl_paths = split

        result = compose_test_then_impl_commits(
            scratch_repo,
            base,
            feature,
            test_paths,
            impl_paths,
            "test(widget): add test_widget",
            "feat(widget): add widget",
        )
        assert result.is_ok
        test_sha, impl_sha = result.danger_ok

        # Working tree never touched.
        assert a_path.stat().st_mtime_ns == before_mtime
        assert not (scratch_repo / "widget.py").exists()
        assert not (scratch_repo / "tests").exists()

        # Commit 1 (test_sha): parent is base, contains ONLY the test file
        # relative to base.
        parents = _run(
            ["git", "rev-parse", f"{test_sha}^@"], scratch_repo
        ).stdout.strip()
        assert parents == base
        changed = _run(
            ["git", "diff", "--name-only", base, test_sha], scratch_repo
        ).stdout.split()
        assert changed == ["tests/test_widget.py"]

        # Commit 2 (impl_sha): parent is commit 1, and its own tree adds
        # widget.py on top -- the FULL diff from base to commit 2 equals
        # both files.
        parents2 = _run(
            ["git", "rev-parse", f"{impl_sha}^@"], scratch_repo
        ).stdout.strip()
        assert parents2 == test_sha
        full_changed = sorted(
            _run(
                ["git", "diff", "--name-only", base, impl_sha], scratch_repo
            ).stdout.split()
        )
        assert full_changed == ["tests/test_widget.py", "widget.py"]

    def test_final_tree_matches_full_squash(self, scratch_repo: Path) -> None:
        """The final commit's tree is byte-identical to what a plain
        single-commit `compose_tree_out_of_tree` squash would have
        produced -- splitting the commit boundary never changes the
        published CONTENT, only its history shape."""
        # frob:tests \
        # tests/unit/test_land_splice_test_then_impl.py::TestComposeTestThenImplCommits\
        # .test_final_tree_matches_full_squash
        from frob.tickets._land_compose import compose_tree_out_of_tree

        base = _run(["git", "rev-parse", "main"], scratch_repo).stdout.strip()
        feature = _run(["git", "rev-parse", "feature"], scratch_repo).stdout.strip()

        squashed = compose_tree_out_of_tree(scratch_repo, base, feature)
        assert squashed.is_ok
        squash_tree = _run(
            ["git", "rev-parse", f"{squashed.danger_ok}^{{tree}}"], scratch_repo
        ).stdout.strip()

        split = classify_test_then_impl_paths(["tests/test_widget.py", "widget.py"])
        assert split is not None
        test_paths, impl_paths = split
        result = compose_test_then_impl_commits(
            scratch_repo,
            base,
            feature,
            test_paths,
            impl_paths,
            "test(widget): add test_widget",
            "feat(widget): add widget",
        )
        assert result.is_ok
        _test_sha, impl_sha = result.danger_ok
        split_tree = _run(
            ["git", "rev-parse", f"{impl_sha}^{{tree}}"], scratch_repo
        ).stdout.strip()

        assert split_tree == squash_tree
