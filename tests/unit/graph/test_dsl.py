"""Tests for backslash line-continuation in the comment DSL (T-0286).

The bulk of the DSL parser's tests live in `tests/test_graph.py::TestDsl`
(this file does not duplicate them); this file covers only the
continuation-folding behavior added in `frob.graph.dsl._fold_continuations`
and its integration into `parse_directives` -- see
docs/guides/extending/comment-dsl-directives.md for the syntax writeup.
"""

from __future__ import annotations

from pathlib import Path

from frob.graph._models import EdgeKind
from frob.graph.dsl import (
    _RESERVED_MARKER_VERBS,
    _resolve_block_srcs,
    fold_comment_runs,
    parse_directives,
)
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
            '    # frob:secret-fake reason="fabricated fixture token"\n'
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


class TestProtocolDeclarations:
    """`frob:protocol`/`frob:transition`/`frob:requires` (T-0744)."""

    def test_declared_protocol_round_trips(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        src = (
            '# frob:protocol conn states="idle,open,closed" initial="idle"\n'
            "def use_conn() -> None:\n"
            "    pass\n"
            "\n"
            '# frob:transition proto="conn" from="idle" to="open"\n'
            "def open_conn() -> None:\n"
            "    pass\n"
            "\n"
            '# frob:requires proto="conn" state="open"\n'
            "def send() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        by_kind = {e.kind: e for e in edges}
        assert by_kind[EdgeKind.PROTOCOL].target == "conn"
        assert by_kind[EdgeKind.PROTOCOL].attrs["states"] == "idle,open,closed"
        assert by_kind[EdgeKind.PROTOCOL].attrs["initial"] == "idle"
        assert by_kind[EdgeKind.PROTOCOL].attrs["cleanup"] == "on-error"
        assert by_kind[EdgeKind.TRANSITION].target == "conn"
        assert by_kind[EdgeKind.TRANSITION].attrs["from"] == "idle"
        assert by_kind[EdgeKind.TRANSITION].attrs["to"] == "open"
        assert by_kind[EdgeKind.REQUIRES].target == "conn"
        assert by_kind[EdgeKind.REQUIRES].attrs["state"] == "open"

    def test_protocol_missing_states_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs_verb_error
        src = '# frob:protocol conn initial="idle"\ndef use_conn() -> None:\n    pass\n'
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "states" in malformed[0].reason

    def test_protocol_initial_not_in_states_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs_verb_error
        src = (
            '# frob:protocol conn states="idle,open" initial="closed"\n'
            "def use_conn() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "initial" in malformed[0].reason

    def test_protocol_bad_cleanup_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs_verb_error
        src = (
            '# frob:protocol conn states="idle,open" initial="idle" '
            'cleanup="whenever"\n'
            "def use_conn() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "cleanup" in malformed[0].reason

    def test_transition_missing_attrs_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs_verb_error
        src = (
            '# frob:transition proto="conn" from="idle"\n'
            "def open_conn() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "to" in malformed[0].reason

    def test_requires_missing_state_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_attrs_verb_error
        src = '# frob:requires proto="conn"\ndef send() -> None:\n    pass\n'
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "state" in malformed[0].reason

    def test_unbound_protocol_is_a_loud_error_not_a_skip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_protocol_coherence
        # T-0744 acceptance: a declared protocol with zero transition/
        # requires bindings anywhere in the file is a malformed-directive
        # ERROR, never silently accepted.
        src = (
            '# frob:protocol conn states="idle,open" initial="idle"\n'
            "def use_conn() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert any(e.kind == EdgeKind.PROTOCOL for e in edges)
        assert len(malformed) == 1
        assert "zero" in malformed[0].reason
        assert "conn" in malformed[0].reason

    def test_bound_protocol_is_not_flagged_unbound(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_protocol_coherence
        src = (
            '# frob:protocol conn states="idle,open" initial="idle"\n'
            "def use_conn() -> None:\n"
            "    pass\n"
            "\n"
            '# frob:requires proto="conn" state="open"\n'
            "def send() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        _edges, malformed = parse_directives(pf)
        assert not malformed


# frob:ticket T-0809
class TestResourceDirectives:
    """`frob:acquire`/`frob:release`/`frob:escapes` (T-0809): bare-target
    verbs, same grammar shape as `frob:doc`/`frob:ticket` -- no required
    attributes."""

    def test_acquire_release_escapes_round_trip(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        src = (
            "# frob:acquire fd\n"
            "# frob:release lock\n"
            "# frob:escapes conn\n"
            "def open_fd() -> None:\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        by_kind = {e.kind: e for e in edges}
        assert by_kind[EdgeKind.ACQUIRE].target == "fd"
        assert by_kind[EdgeKind.RELEASE].target == "lock"
        assert by_kind[EdgeKind.ESCAPES].target == "conn"
        assert all(e.src.endswith("::open_fd") for e in edges)

    def test_acquire_missing_target_is_malformed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_parse_line
        src = "# frob:acquire\ndef open_fd() -> None:\n    pass\n"
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not edges
        assert len(malformed) == 1
        assert "acquire" in malformed[0].reason


class TestInitDeinitInference:
    """Zero-declaration init/deinit name-pattern inference (T-0744)."""

    def test_init_deinit_pair_infers_a_protocol(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_infer_init_deinit_protocols
        src = (
            "def foo_init() -> None:\n    pass\n\ndef foo_deinit() -> None:\n    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        protocol_edges = [e for e in edges if e.kind == EdgeKind.PROTOCOL]
        transition_edges = [e for e in edges if e.kind == EdgeKind.TRANSITION]
        assert len(protocol_edges) == 1
        assert protocol_edges[0].attrs["inferred"] == "true"
        assert len(transition_edges) == 2
        srcs = {e.src for e in transition_edges}
        assert srcs == {f"{pf.path}::foo_init", f"{pf.path}::foo_deinit"}

    def test_open_close_pair_also_infers(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_infer_init_deinit_protocols
        src = (
            "def bar_open() -> None:\n    pass\n\ndef bar_close() -> None:\n    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert any(e.kind == EdgeKind.PROTOCOL for e in edges)

    def test_unpaired_init_infers_nothing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::_infer_init_deinit_protocols
        # No general-machine inference: a lone *_init with no matching
        # *_deinit in the file must not synthesize a protocol.
        src = "def foo_init() -> None:\n    pass\n"
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert not any(e.kind == EdgeKind.PROTOCOL for e in edges)


class TestFoldCommentRuns:
    """`fold_comment_runs` (T-0441): same fold as `_fold_continuations`, plus
    the physical-line count each logical entry consumed."""

    def test_run_length_matches_consumed_physical_lines(self) -> None:
        # frob:tests src/frob/graph/dsl.py::fold_comment_runs
        lines = [
            (1, 'frob:waive RULE-1 reason="this reason is intentionally \\', "", 0),
            (2, 'long so it would overflow the ruff line-length limit"', "", 1),
            (3, "frob:ticket T-0002", "", 2),
        ]
        folded = fold_comment_runs(lines)
        assert len(folded) == 2
        text0, lineno0, _src0, count0 = folded[0]
        assert lineno0 == 1
        assert count0 == 2
        assert text0 == (
            'frob:waive RULE-1 reason="this reason is intentionally '
            'long so it would overflow the ruff line-length limit"'
        )
        text1, lineno1, _src1, count1 = folded[1]
        assert lineno1 == 3
        assert count1 == 1
        assert text1 == "frob:ticket T-0002"

    def test_single_line_run_has_count_one(self) -> None:
        # frob:tests src/frob/graph/dsl.py::fold_comment_runs
        lines = [(1, "frob:ticket T-0441", "", 0)]
        folded = fold_comment_runs(lines)
        assert folded == [("frob:ticket T-0441", 1, "", 1)]

    def test_matches_fold_continuations_text_and_lineno(self) -> None:
        # frob:tests src/frob/graph/dsl.py::_fold_continuations
        from frob.graph.dsl import _fold_continuations

        lines = [
            (1, 'frob:waive RULE-1 reason="a \\', "", 0),
            (2, 'b"', "", 1),
        ]
        folded_runs = fold_comment_runs(lines)
        folded_plain = _fold_continuations(lines)
        assert [(t, ln, s) for t, ln, s, _c in folded_runs] == folded_plain


class TestVerbShapedContinuationProse:
    """T-0987: a continuation line whose prose happens to start with a
    `frob:`-shaped token that is not a registered verb (e.g. the literal
    substring `frob:describes` inside a `reason="..."`) must fold as
    continuation content, never misparse as a bogus new directive."""

    def test_frob_describes_prose_at_continuation_line_start_folds(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # Minimal repro shape verified against src/frob/vet/_allow.py after
        # T-0985's recompaction shifted the wrap boundary so
        # "frob:describes" became the first word of its own physical line.
        src = (
            "def foo() -> None:\n"
            '    # frob:waive COV007 reason="docs section individually \\\n'
            "    # frob:describes this private helper by name (T-0529) -- \\\n"
            '    # a deliberate architecture doc"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].attrs["reason"] == (
            "docs section individually frob:describes this private helper "
            "by name (T-0529) -- a deliberate architecture doc"
        )

    def test_frob_describes_prose_repro_shape_from_dup_core(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # Minimal repro shape verified against src/frob/dup/_core.py's own
        # T-0985-recompaction cascade.
        src = (
            "def bar() -> None:\n"
            '    # frob:waive COV007 reason="rust-core section \\\n'
            "    # frob:describes each private frob_core shim by name \\\n"
            '    # (T-0524) -- deliberate"\n'
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 1
        assert edges[0].attrs["reason"] == (
            "rust-core section frob:describes each private frob_core shim "
            "by name (T-0524) -- deliberate"
        )

    def test_stacked_directives_still_parse_independently(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # Genuine adjacent directives in one comment block (this repo's
        # widespread frob:ticket/frob:tests stacking convention) must still
        # parse as separate edges, not get swallowed by the widened
        # continuation exception.
        src = (
            "def baz() -> None:\n"
            "    # frob:ticket T-0286\n"
            "    # frob:tests tests/unit/graph/test_dsl.py::TestContinuation.\\\n"
            "    # test_long_reason_continues_across_lines\n"
            "    pass\n"
        )
        pf = parse_file(_write(tmp_path, "a.py", src)).danger_ok
        edges, malformed = parse_directives(pf)
        assert not malformed
        assert len(edges) == 2
        kinds = {e.kind for e in edges}
        assert kinds == {EdgeKind.TICKET, EdgeKind.TESTS}
        tests_edge = next(e for e in edges if e.kind == EdgeKind.TESTS)
        assert tests_edge.target == (
            "tests/unit/graph/test_dsl.py::TestContinuation."
            "test_long_reason_continues_across_lines"
        )

    def test_unrelated_directives_corruption_repro_still_rejects_fold(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # T-0286's own corruption repro must still refuse to fold two
        # independently-valid directives on physically adjacent lines.
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

    def test_property_wrap_at_every_width_preserves_reason(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # Property-style: re-wrap a real directive whose reason prose
        # contains a `frob:describes`-shaped substring at every width from
        # the tightest that can still hold one word per line up to a wide
        # single-line fit, and assert parsing is stable (zero malformed,
        # same recovered reason) at every width -- not just the one
        # verified repro shape.
        from frob.gates._fmt_directives import canonicalize_text

        logical = (
            'frob:waive COV007 reason="docs section individually '
            "frob:describes this private helper by name (T-0529) -- a "
            'deliberate architecture doc, not accidental drift"'
        )
        src_template = "def foo() -> None:\n    # {}\n    pass\n"
        original = src_template.format(logical)
        path = tmp_path / "a.py"
        expected_reason = (
            "docs section individually frob:describes this private helper "
            "by name (T-0529) -- a deliberate architecture doc, not "
            "accidental drift"
        )
        for limit in range(20, 120, 4):
            rewritten = canonicalize_text(original, path=str(path), limit=limit)
            path.write_text(rewritten)
            pf = parse_file(path).danger_ok
            edges, malformed = parse_directives(pf)
            assert not malformed, f"limit={limit} produced malformed: {malformed}"
            assert len(edges) == 1
            assert edges[0].attrs["reason"] == expected_reason
