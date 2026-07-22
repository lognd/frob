"""Tests for backslash line-continuation in the comment DSL (T-0286).

The bulk of the DSL parser's tests live in `tests/test_graph.py::TestDsl`
(this file does not duplicate them); this file covers only the
continuation-folding behavior added in `frob.graph.dsl._fold_continuations`
and its integration into `parse_directives` -- see
docs/guides/extending/comment-dsl-directives.md for the syntax writeup.
"""

from __future__ import annotations

from pathlib import Path

from frob.graph.dsl import _RESERVED_MARKER_VERBS, _resolve_block_srcs, parse_directives
from frob.lang import parse_file
from frob.lang._models import ParsedFile, RawComment, RawSymbol, SymbolKind


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

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
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

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
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

    def test_unrelated_directives_on_consecutive_lines_do_not_fold(
        self, tmp_path: Path
    ) -> None:
        # Reviewer-reported corruption bug (T-0286): two directives on
        # DIFFERENT symbols that happen to sit on physically consecutive
        # lines -- the first coincidentally ending in a trailing backslash
        # -- must NOT be folded together just because the line numbers are
        # adjacent. Folding is only valid within a single originating
        # comment run; here the two comments belong to different
        # `RawComment`s bound to different symbols (class A vs class B), so
        # both must parse as independent, correct edges.
        src = (
            "class A:\n"
            "    x = 1  # frob:ticket T-0001\\\n"
            "class B:  # frob:ticket T-0002\n"
            "    y = 2\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 2
        targets = {edge.target for edge in edges}
        assert targets == {"T-0001\\", "T-0002"}


class TestReservedMarkerVerbs:
    """Verbs another subsystem owns as a literal marker (T-0294) must parse
    to neither an edge nor a `MalformedDirective` -- the DSL parser silently
    ignores them rather than reporting "unknown verb"."""

    def test_secret_fake_is_silently_skipped(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        assert "secret-fake" in _RESERVED_MARKER_VERBS
        src = (
            "def foo() -> None:\n"
            "    # frob:secret-fake\n"
            '    token = "sk-fake-1234567890"\n'
            "    return token\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert not malformed

    def test_unreserved_unknown_verb_still_reports_malformed(
        self, tmp_path: Path
    ) -> None:
        # Control case: an ordinary unregistered verb (not in
        # `_RESERVED_MARKER_VERBS`) must still be reported, so the reserved
        # list is an explicit allowlist, not a general parser laxness.
        src = "def foo() -> None:\n    # frob:not-a-real-verb target\n    pass\n"
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "unknown verb" in malformed[0].reason


class TestNoqaTail:
    """A directive sharing a physical line with a linter-suppression comment
    (`# noqa: ...`) must still parse, not be dropped as malformed (T-0309)."""

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_waive_with_trailing_noqa_parses(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs
        src = (
            "def foo() -> None:\n"
            '    # frob:waive RULE-1 reason="x"  # noqa: E501\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "RULE-1"
        assert edges[0].attrs["reason"] == "x"

    # frob:waive DUP001 reason="parallel graph/dsl test cases sharing an \
    # arrange-act scaffold; extracting would obscure per-case intent"
    def test_tests_with_trailing_bare_noqa_binds(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs
        src = (
            "def foo() -> None:\n"
            '    # frob:tests path::Sym kind="unit"  # noqa\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].target == "path::Sym"
        assert edges[0].attrs["kind"] == "unit"

    def test_hash_inside_quoted_value_is_preserved(self, tmp_path: Path) -> None:
        # A '#' inside a quoted attribute value is content, not a comment
        # tail -- it must survive into the parsed attribute unchanged, even
        # though the same character would be stripped as a noqa tail if it
        # appeared outside the quotes.
        src = (
            "def foo() -> None:\n"
            '    # frob:waive RULE-1 reason="uses #hashtag"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].attrs["reason"] == "uses #hashtag"


class TestBlockBinding:
    """A `frob:doc` (or any) directive found anywhere in a contiguous
    comment block above a symbol must bind to that symbol, regardless of
    how many other directive lines sit between it and the symbol (T-0313)."""

    def test_doc_before_two_ticket_lines_still_binds_via_generic_walker(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # Regression proof at the real-language-walker level: the generic
        # tree-sitter path (python here) already block-widens `following`
        # correctly, so this must pass both before and after T-0313 -- it
        # guards against a future regression in either layer.
        src = (
            "class A:\n"
            "    # frob:doc docs/x.md#y\n"
            "    # frob:ticket T-0001\n"
            "    # frob:ticket T-0002\n"
            "    def foo(self) -> None:\n"
            "        pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        doc_edges = [e for e in edges if e.kind.value == "doc"]
        assert len(doc_edges) == 1
        assert doc_edges[0].src.endswith("::A.foo")

    def test_narrow_following_window_propagates_backward_through_run(self) -> None:
        # frob:tests src/frob/graph/dsl.py::_resolve_block_srcs
        # Reproduces the actual reported failure mode: a walker (like
        # frob.lang._walk_strata) that resolves `following` against each
        # comment's OWN line, not the whole stacked block's end line. Only
        # the comment on the line directly above the symbol resolves
        # `following` on its own; the two lines further up must inherit
        # that binding via backward propagation through the unbroken run.
        symbols = (
            RawSymbol(
                qualname="FooNode",
                kind=SymbolKind.CLASS,
                public=True,
                span=(4, 6),
                sig_tokens=(),
                body_tokens=(),
                doc_text="",
            ),
        )
        comments = (
            RawComment(
                text="frob:doc docs/x.md#y", span=(1, 1), enclosing=None, following=None
            ),
            RawComment(
                text="frob:ticket T-0001", span=(2, 2), enclosing=None, following=None
            ),
            RawComment(
                text="frob:ticket T-0002",
                span=(3, 3),
                enclosing=None,
                following="FooNode",
            ),
        )
        pf = ParsedFile(
            path="a.strata",
            language="strata",
            symbols=symbols,
            comments=comments,
            content_hash="x",
        )
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 3
        assert all(e.src == "a.strata::FooNode" for e in edges)

    def test_gap_still_breaks_propagation(self) -> None:
        # frob:tests src/frob/graph/dsl.py::_resolve_block_srcs
        # A genuine gap (non-adjacent line number) between two comments
        # must NOT be bridged by propagation -- only an unbroken
        # line-adjacent run may inherit a resolved `following` binding.
        comments = (
            RawComment(
                text="frob:doc docs/x.md#y", span=(1, 1), enclosing=None, following=None
            ),
            # a gap here (blank/code line at 2-4) breaks the run
            RawComment(
                text="frob:ticket T-0002",
                span=(5, 5),
                enclosing=None,
                following="FooNode",
            ),
        )
        resolved = _resolve_block_srcs(comments, "a.strata")
        assert resolved[1] == "a.strata::FooNode"
        assert resolved[0] == "a.strata"  # bare path: no enclosing, no propagation


class TestDebtTodoCoherence:
    """`frob:debt`/`frob:todo` coherence (T-0526): an unpaired debt implicitly
    registers a todo, and a mismatched explicit pairing is a DEBT001-shaped
    `MalformedDirective`."""

    def test_unpaired_debt_registers_implicit_todo(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_debt_todo_coherence
        src = (
            "def foo() -> None:\n"
            '    # frob:debt RULE-1 reason="temp gap" ticket="T-0001"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 2
        debt = next(e for e in edges if e.kind == "debt")
        todo = next(e for e in edges if e.kind == "todo")
        assert todo.src == debt.src
        assert todo.target == "T-0001"
        assert todo.attrs["implicit"] == "debt"

    def test_explicit_paired_todo_same_ticket_no_implicit_duplicate(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::_debt_todo_coherence
        src = (
            "def foo() -> None:\n"
            '    # frob:debt RULE-1 reason="temp gap" ticket="T-0001"\n'
            "    # frob:todo T-0001\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        todo_edges = [e for e in edges if e.kind == "todo"]
        assert len(todo_edges) == 1
        assert "implicit" not in todo_edges[0].attrs

    def test_mismatched_explicit_todo_is_debt001_shaped_malformed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::_debt_todo_coherence
        src = (
            "def foo() -> None:\n"
            '    # frob:debt RULE-1 reason="temp gap" ticket="T-0001"\n'
            "    # frob:todo T-0002\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert len(malformed) == 1
        assert "frob:debt" in malformed[0].reason
        assert "T-0001" in malformed[0].reason
        assert "T-0002" in malformed[0].reason


class TestDeprecatedDirective:
    """`frob:deprecated <since> sunset="YYYY-MM-DD" ticket="T-####"` (T-0576):
    the required-attrs parse (mirroring `frob:debt`'s own required-attrs
    check) and its `sunset=` date-shape validation."""

    def test_well_formed_directive_parses_to_deprecated_edge(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs
        src = (
            "def foo() -> None:\n"
            '    # frob:deprecated 0.70.0 sunset="2099-01-01" ticket="T-0001" '
            'reason="use bar instead"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        edge = next(e for e in edges if e.kind == "deprecated")
        assert edge.target == "0.70.0"
        assert edge.attrs["sunset"] == "2099-01-01"
        assert edge.attrs["ticket"] == "T-0001"
        assert edge.attrs["reason"] == "use bar instead"

    def test_missing_sunset_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs
        src = (
            "def foo() -> None:\n"
            '    # frob:deprecated 0.70.0 ticket="T-0001"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "sunset" in malformed[0].reason

    def test_missing_ticket_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs
        src = (
            "def foo() -> None:\n"
            '    # frob:deprecated 0.70.0 sunset="2099-01-01"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "ticket" in malformed[0].reason

    def test_non_date_sunset_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs
        src = (
            "def foo() -> None:\n"
            '    # frob:deprecated 0.70.0 sunset="Q1-2099" ticket="T-0001"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "sunset" in malformed[0].reason
