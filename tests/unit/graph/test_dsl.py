"""Tests for backslash line-continuation in the comment DSL (T-0286).

The bulk of the DSL parser's tests live in `tests/test_graph.py::TestDsl`
(this file does not duplicate them); this file covers only the
continuation-folding behavior added in `frob.graph.dsl._fold_continuations`
and its integration into `parse_directives` -- see
docs/guides/extending/comment-dsl-directives.md for the syntax writeup.
"""

from __future__ import annotations

from pathlib import Path

from frob.graph.dsl import parse_directives
from frob.lang import parse_file


def _write(root: Path, rel: str, text: str) -> Path:
    """Write `text` to `root/rel`, creating parent dirs, and return the path."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestContinuation:
    """`frob:<verb> ... \\` folds onto the following comment line (T-0286)."""

    def test_long_reason_continues_across_lines(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        src = (
            "def foo() -> None:\n"
            '    # frob:waive RULE-1 reason="this reason is intentionally \\\n'
            '    # long so it would overflow the ruff line-length limit"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].attrs["reason"] == (
            "this reason is intentionally long so it would overflow the "
            "ruff line-length limit"
        )

    def test_folded_directive_reports_first_physical_lineno(
        self, tmp_path: Path
    ) -> None:
        # A malformed folded directive (unknown verb) must report the line
        # number of the FIRST physical line of the run, not the
        # continuation line it was folded from.
        src = (
            "def foo() -> None:\n"
            '    # frob:bogus target reason="split across \\\n'
            '    # two lines"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert malformed[0].line == 2

    def test_join_uses_empty_string_not_space(self, tmp_path: Path) -> None:
        # No space is inserted at the join point -- a continuation that
        # wants a space must put it before the trailing backslash. Here the
        # first line ends immediately at the backslash (no trailing space),
        # so the joined reason has no gap between "left" and "right".
        src = (
            "def foo() -> None:\n"
            '    # frob:waive RULE-1 reason="left\\\n'
            '    # right"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert edges[0].attrs["reason"] == "leftright"

    def test_three_line_continuation(self, tmp_path: Path) -> None:
        # Continuation folds across more than one hop.
        src = (
            "def foo() -> None:\n"
            '    # frob:waive RULE-1 reason="a\\\n'
            "    # b\\\n"
            '    # c"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert edges[0].attrs["reason"] == "abc"

    def test_normal_single_line_directive_unchanged(self, tmp_path: Path) -> None:
        # Regression: a directive with no trailing backslash must parse
        # byte-for-byte the same as before continuation folding existed.
        src = """def foo() -> None:
    # frob:waive RULE-1 reason="known issue"
    pass
"""
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].attrs["reason"] == "known issue"

    def test_dangling_backslash_on_last_comment_line_is_literal(
        self, tmp_path: Path
    ) -> None:
        # A trailing backslash on the LAST physical line of a comment has
        # nothing to fold into -- per T-0286's design decision this is
        # treated LITERALLY (the backslash stays in the parsed target/attr
        # text) rather than reported as malformed.
        src = "def foo() -> None:\n    # frob:ticket T-0042\\\n    pass\n"
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "T-0042\\"

    def test_crlf_before_trailing_backslash_is_safe(self, tmp_path: Path) -> None:
        # A trailing `\` immediately before a CRLF line ending must still
        # fold correctly -- no stray `\r` should leak into the joined text.
        src = (
            "def foo() -> None:\r\n"
            '    # frob:waive RULE-1 reason="crlf \\\r\n'
            '    # safe"\r\n'
            "    pass\r\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].attrs["reason"] == "crlf safe"
        assert "\r" not in edges[0].attrs["reason"]

    def test_verb_agnostic_multiline_tests_directive(self, tmp_path: Path) -> None:
        # Continuation folding is not waive-specific -- prove it also works
        # for frob:tests.
        src = (
            "def foo() -> None:\n"
            "    # frob:tests tests/a.py::test_foo \\\n"
            '    # kind="integration"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "tests/a.py::test_foo"
        assert edges[0].attrs["kind"] == "integration"
