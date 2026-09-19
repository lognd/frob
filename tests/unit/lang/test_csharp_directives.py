"""C# comment-DSL directive parity (T-4507): `//`, `///` XML-doc, and
`/* */` comments carry `frob:doc`/`frob:tests`/`frob:todo`/`frob:ticket`/
`frob:waive` exactly like python's `#` comments, via the same
language-agnostic `frob.lang._extract`/`frob.graph.dsl.parse_directives`
path python/rust/etc. already go through -- see
tests/fixtures/lang/csharp/directives.cs for the static per-comment-form
fixture this class parses end to end.
"""

from __future__ import annotations

from pathlib import Path

from frob.graph._models import EdgeKind
from frob.graph.dsl import parse_directives
from frob.lang import parse_file

# frob:ticket T-4507
_FIXTURE = Path("tests/fixtures/lang/csharp/directives.cs")


# frob:ticket T-4507
# frob:waive DUP002 reason="T-4507: parity tests are deliberately near-identical in \
# shape -- each proves the SAME directive-binding behavior for a DIFFERENT \
# comment-delimiter form (//, ///, /* */) or a different directive verb (doc, todo, \
# tests, ticket, waive) against one shared static fixture; collapsing them into one \
# parametrized/shared-helper test would hide which specific comment form or verb \
# regressed when one assertion fails"
class TestCSharpDirectiveParity:
    """Every directive verb resolves to an `Edge`, never a
    `MalformedDirective`, from each C# comment form (T-4507)."""

    # frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_slash_doc_directive_binds  # noqa: E501
    # frob:ticket T-4507
    def test_slash_doc_directive_binds(self) -> None:
        """A `// frob:doc ...` line above a method records a DOC edge
        targeting the method, identically to python's `# frob:doc`."""
        parsed = parse_file(_FIXTURE).danger_ok
        edges, malformed = parse_directives(parsed)
        docs = [e for e in edges if e.kind == EdgeKind.DOC and "SlashDoc" in e.src]
        assert docs, (edges, malformed)
        assert docs[0].target == "docs/modules/lang.md#per-language-walker-notes"

    # frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_xml_doc_slash_doc_directive_binds  # noqa: E501
    # frob:ticket T-4507
    def test_xml_doc_slash_doc_directive_binds(self) -> None:
        """A `/// frob:doc ...` XML-doc line above a method records the
        same DOC edge as the plain `//` form."""
        parsed = parse_file(_FIXTURE).danger_ok
        edges, malformed = parse_directives(parsed)
        docs = [e for e in edges if e.kind == EdgeKind.DOC and "XmlDocDoc" in e.src]
        assert docs, (edges, malformed)

    # frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_block_comment_doc_directive_binds  # noqa: E501
    # frob:ticket T-4507
    def test_block_comment_doc_directive_binds(self) -> None:
        """A `/* frob:doc ... */` block comment above a method records
        the same DOC edge as the line-comment forms."""
        parsed = parse_file(_FIXTURE).danger_ok
        edges, malformed = parse_directives(parsed)
        docs = [e for e in edges if e.kind == EdgeKind.DOC and "BlockDoc" in e.src]
        assert docs, (edges, malformed)

    # frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_xml_doc_todo_free_text_note_is_accepted  # noqa: E501
    # frob:ticket T-4507
    def test_xml_doc_todo_free_text_note_is_accepted(self) -> None:
        """A `/// frob:todo T-#### <free text>` line parses as a
        deferred-work directive edge, not a `MalformedDirective`
        (T-3856's free-text fix applies to XML-doc comments the same as
        every other comment form)."""
        parsed = parse_file(_FIXTURE).danger_ok
        edges, malformed = parse_directives(parsed)
        todos = [e for e in edges if e.kind == EdgeKind.TODO and "XmlDocTodo" in e.src]
        assert todos, (edges, malformed)
        assert not any("XmlDocTodo" in m.reason for m in malformed)

    # frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_slash_tests_directive_with_noqa_tail_binds  # noqa: E501
    # frob:ticket T-4507
    def test_slash_tests_directive_with_noqa_tail_binds(self) -> None:
        """A `// frob:tests <node>  # noqa: E501` line binds a TESTS edge
        with the noqa-style tail stripped, not folded into the target."""
        parsed = parse_file(_FIXTURE).danger_ok
        edges, malformed = parse_directives(parsed)
        tests_edges = [
            e for e in edges if e.kind == EdgeKind.TESTS and "SlashTests" in e.src
        ]
        assert tests_edges, (edges, malformed)
        assert "noqa" not in tests_edges[0].target

    # frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_stacked_directive_run_binds_both_lines  # noqa: E501
    # frob:ticket T-4507
    def test_stacked_directive_run_binds_both_lines(self) -> None:
        """Two stacked `//` directive lines directly above one method
        (a "directive run", no blank line between them) both bind to that
        SAME method -- neither line is lost to the other."""
        parsed = parse_file(_FIXTURE).danger_ok
        edges, malformed = parse_directives(parsed)
        run_edges = [e for e in edges if "MultiLineRun" in e.src]
        kinds = {e.kind for e in run_edges}
        assert EdgeKind.TICKET in kinds, (edges, malformed)
        assert EdgeKind.DOC in kinds, (edges, malformed)

    # frob:tests tests/unit/lang/test_csharp_directives.py::TestCSharpDirectiveParity.test_xml_doc_waive_directive_on_class_binds  # noqa: E501
    # frob:ticket T-4507
    def test_xml_doc_waive_directive_on_class_binds(self) -> None:
        """A `frob:waive` directive written inside a `///` XML `<summary>`
        block above a class resolves as a WAIVE edge targeting the class,
        the same as a plain-comment waiver."""
        parsed = parse_file(_FIXTURE).danger_ok
        edges, malformed = parse_directives(parsed)
        waives = [e for e in edges if e.kind == EdgeKind.WAIVE and "Widget" in e.src]
        assert waives, (edges, malformed)
        assert waives[0].attrs.get("rule") == "DIRTEST001" or "DIRTEST001" in (
            waives[0].target
        )
