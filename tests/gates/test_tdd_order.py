"""T-3009: TDD001, the ordering check that a `frob:tests` edge's test
symbol must be introduced BEFORE the artifact it verifies, as a checkable
git-history fact (T-3004 section 7). Every fixture here builds a REAL
tiny git repo with a controlled commit sequence (never a mocked git
spawn) so these tests exercise the actual ast-parse/ancestry commands
this module runs at land time."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.findings import Severity
from frob.gates._tdd_order import (
    TDDOrder,
    _ast_qualnames,
    classify_order,
    resolve_symbol_introduction,
    symref_path,
    symref_qualname,
    tdd_order_violations,
)
from frob.graph._models import Edge, EdgeKind


def _git(root: Path, *args: str) -> None:
    """Run one git command in `root`, raising on any nonzero exit --
    these are fixture-construction calls, a failure here is a broken
    test, not something to degrade gracefully around."""
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        capture_output=True,
        text=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.com",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.com",
            "PATH": "/usr/bin:/bin",
        },
    )


def _init_repo(root: Path) -> None:
    """A fresh, empty git repo at `root`, default branch `main`."""
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")


def _commit_file(root: Path, rel: str, content: str, message: str) -> str:
    """Write `content` to `rel`, commit it, and return the new commit's
    sha -- the one fixture primitive every test below composes."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _git(root, "add", rel)
    _git(root, "commit", "-q", "-m", message)
    return subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


# frob:ticket T-3009
class TestSymrefHelpers:
    # frob:ticket T-3009
    def test_symref_path_splits_on_double_colon(self) -> None:
        assert symref_path("src/m.py::Foo.bar") == "src/m.py"
        assert symref_path("src/m.py") == "src/m.py"

    # frob:ticket T-3009
    def test_symref_qualname_keeps_the_full_dotted_path(self) -> None:
        assert symref_qualname("src/m.py::Foo.bar") == "Foo.bar"
        assert symref_qualname("src/m.py::bar") == "bar"
        assert symref_qualname("src/m.py") is None


# frob:ticket T-3009
class TestAstQualnames:
    # frob:ticket T-3009
    def test_collects_nested_dotted_qualnames(self) -> None:
        # frob:tests tests/gates/test_tdd_order.py::TestAstQualnames.test_collects_nested_dotted_qualnames  # noqa: E501
        source = (
            "def widget():\n"
            "    pass\n\n\n"
            "class Foo:\n"
            "    def bar(self):\n"
            "        pass\n"
        )
        assert _ast_qualnames(source) == {"widget", "Foo", "Foo.bar"}

    # frob:ticket T-3009
    def test_a_bare_mention_in_a_docstring_or_comment_is_not_a_definition(self) -> None:
        source = (
            '"""this module mentions widget in prose, but never defines it."""\n'
            "# widget is also mentioned here, in a comment\n"
            "x = 'widget'\n"
        )
        assert "widget" not in _ast_qualnames(source)

    # frob:ticket T-3009
    def test_unparseable_source_yields_an_empty_set(self) -> None:
        assert _ast_qualnames("def broken(:\n") == set()


# frob:ticket T-3009
class TestResolveSymbolIntroduction:
    # frob:ticket T-3009
    def test_resolves_the_commit_that_added_the_symbol(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _commit_file(tmp_path, "m.py", "def unrelated():\n    pass\n", "unrelated")
        added_sha = _commit_file(
            tmp_path,
            "m.py",
            "def unrelated():\n    pass\n\n\ndef widget():\n    pass\n",
            "add widget",
        )
        _commit_file(
            tmp_path,
            "m.py",
            "def unrelated():\n    pass\n\n\ndef widget():\n    return 1\n",
            "tweak widget",
        )
        resolved = resolve_symbol_introduction(tmp_path, "m.py::widget")
        assert resolved == added_sha

    # frob:ticket T-3009
    def test_returns_none_for_a_symbol_never_added(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _commit_file(tmp_path, "m.py", "def real():\n    pass\n", "seed")
        assert resolve_symbol_introduction(tmp_path, "m.py::phantom") is None
        assert resolve_symbol_introduction(tmp_path, "missing.py::real") is None

    # frob:ticket T-3009
    def test_a_mere_textual_mention_does_not_count_as_introduction(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/gates/test_tdd_order.py::TestResolveSymbolIntroduction.test_a_mere_textual_mention_does_not_count_as_introduction  # noqa: E501
        _init_repo(tmp_path)
        # `widget` appears as TEXT here (docstring + comment + string
        # literal) but is never actually DEFINED -- a lexical `git log
        # -S` pickaxe would false-positive on this commit; the real
        # ast-based resolver must not.
        _commit_file(
            tmp_path,
            "m.py",
            '"""mentions widget here, but does not define it."""\n'
            "# widget is also named in this comment\n"
            "x = 'widget'\n",
            "mentions widget in prose only",
        )
        defining_sha = _commit_file(
            tmp_path, "m.py", "def widget():\n    pass\n", "actually define widget"
        )
        assert resolve_symbol_introduction(tmp_path, "m.py::widget") == defining_sha


# frob:ticket T-3009
class TestClassifyOrder:
    # frob:ticket T-3009
    def test_fires_when_implementation_precedes_test(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        impl_sha = _commit_file(tmp_path, "m.py", "x = 1\n", "impl first")
        test_sha = _commit_file(tmp_path, "t.py", "y = 2\n", "test second")
        assert (
            classify_order(tmp_path, artifact_commit=impl_sha, test_commit=test_sha)
            is TDDOrder.IMPLEMENTATION_FIRST
        )

    # frob:ticket T-3009
    def test_stays_quiet_when_test_precedes_implementation(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        test_sha = _commit_file(tmp_path, "t.py", "y = 2\n", "test first")
        impl_sha = _commit_file(tmp_path, "m.py", "x = 1\n", "impl second")
        assert (
            classify_order(tmp_path, artifact_commit=impl_sha, test_commit=test_sha)
            is TDDOrder.TEST_FIRST
        )

    # frob:ticket T-3009
    def test_fires_when_commits_are_identical(self, tmp_path: Path) -> None:
        # a same-commit pair is a DETERMINATE non-test-first fact (the
        # squashed-land shape), not an unknown -- see this module's own
        # docstring on why UNRESOLVED would make TDD001 unable to ever
        # fire against its dominant real workflow.
        _init_repo(tmp_path)
        sha = _commit_file(tmp_path, "m.py", "x = 1\ny = 2\n", "squashed test+impl")
        assert (
            classify_order(tmp_path, artifact_commit=sha, test_commit=sha)
            is TDDOrder.IMPLEMENTATION_FIRST
        )

    # frob:ticket T-3009
    def test_reports_unresolved_when_either_commit_is_unresolvable(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        sha = _commit_file(tmp_path, "m.py", "x = 1\n", "only commit")
        assert (
            classify_order(tmp_path, artifact_commit=None, test_commit=sha)
            is TDDOrder.UNRESOLVED
        )
        assert (
            classify_order(tmp_path, artifact_commit=sha, test_commit=None)
            is TDDOrder.UNRESOLVED
        )
        assert (
            classify_order(tmp_path, artifact_commit=None, test_commit=None)
            is TDDOrder.UNRESOLVED
        )

    # frob:ticket T-3009
    def test_reports_unresolved_on_diverged_history(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        base = _commit_file(tmp_path, "base.py", "z = 0\n", "base")
        impl_sha = _commit_file(tmp_path, "m.py", "x = 1\n", "impl on main")
        _git(tmp_path, "checkout", "-q", "-b", "side", base)
        test_sha = _commit_file(tmp_path, "t.py", "y = 2\n", "test on side branch")
        assert (
            classify_order(tmp_path, artifact_commit=impl_sha, test_commit=test_sha)
            is TDDOrder.UNRESOLVED
        )


def _tests_edge(artifact_symref: str, test_symref: str) -> Edge:
    """One `EdgeKind.TESTS` edge, `src`=artifact (the directive's own
    site), `target`=test -- `frob.graph.dsl`'s real binding direction."""
    return Edge(
        src=artifact_symref,
        kind=EdgeKind.TESTS,
        target=test_symref,
        origin=symref_path(artifact_symref),
    )


# frob:ticket T-3009
class TestTddOrderViolations:
    # frob:ticket T-3009
    def test_fires_on_a_planted_implementation_first_pair(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _commit_file(tmp_path, "m.py", "def widget():\n    pass\n", "impl first")
        _commit_file(tmp_path, "t.py", "def test_widget():\n    pass\n", "test second")
        edges = [_tests_edge("m.py::widget", "t.py::test_widget")]
        violations = tdd_order_violations(tmp_path, edges)
        assert len(violations) == 1
        assert violations[0].rule == "TDD001"
        assert violations[0].severity is Severity.ERROR
        assert "m.py::widget" in violations[0].message
        assert "t.py::test_widget" in violations[0].message

    # frob:ticket T-3009
    def test_stays_quiet_on_a_genuine_test_first_pair(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _commit_file(tmp_path, "t.py", "def test_widget():\n    pass\n", "test first")
        _commit_file(tmp_path, "m.py", "def widget():\n    pass\n", "impl second")
        edges = [_tests_edge("m.py::widget", "t.py::test_widget")]
        assert tdd_order_violations(tmp_path, edges) == []

    # frob:ticket T-3009
    def test_fires_when_test_and_implementation_share_a_commit(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _commit_file(
            tmp_path,
            "m.py",
            "def widget():\n    pass\n\n\ndef test_widget():\n    pass\n",
            "squashed land: test and impl in one commit",
        )
        edges = [_tests_edge("m.py::widget", "m.py::test_widget")]
        violations = tdd_order_violations(tmp_path, edges)
        assert len(violations) == 1
        assert violations[0].rule == "TDD001"
        assert violations[0].severity is Severity.ERROR

    # frob:ticket T-3009
    def test_reports_unresolved_rather_than_passing_on_an_unresolvable_pair(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        base = _commit_file(tmp_path, "base.py", "z = 0\n", "base")
        _commit_file(tmp_path, "m.py", "def widget():\n    pass\n", "impl on main")
        _git(tmp_path, "checkout", "-q", "-b", "side", base)
        _commit_file(
            tmp_path, "t.py", "def test_widget():\n    pass\n", "test on side branch"
        )
        edges = [_tests_edge("m.py::widget", "t.py::test_widget")]
        violations = tdd_order_violations(tmp_path, edges)
        assert len(violations) == 1
        assert violations[0].rule == "TDD001"
        assert violations[0].severity is Severity.UNRESOLVED

    # frob:ticket T-3009
    def test_ignores_non_tests_edges(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _commit_file(tmp_path, "m.py", "def widget():\n    pass\n", "impl")
        edge = Edge(
            src="m.py::widget",
            kind=EdgeKind.DOC,
            target="docs/m.md#widget",
            origin="m.py",
        )
        assert tdd_order_violations(tmp_path, [edge]) == []
