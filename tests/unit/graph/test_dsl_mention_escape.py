"""Tests for the `frob:quote(...)` mention escape (T-1970).

The DSL had no mention/use distinction: prose ABOUT a directive was
parsed AS one. `frob:quote(...)` is the one explicit escape, recognized
by `frob.graph.dsl.mask_frob_mentions` and honored by every scanner that
reads directive-shaped text -- this file covers the DSL parser itself
(`parse_directives`/`markdown_anchors`); `tests/test_tickets_live_
tracker.py` covers the separate `frob.tickets._live_tracker` citation
scan.
"""
# frob:ticket T-1970

from __future__ import annotations

from pathlib import Path

from frob.graph._models import EdgeKind
from frob.graph.dsl import markdown_anchors, mask_frob_mentions, parse_directives
from frob.lang import parse_file


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


class TestMaskFrobMentions:
    def test_masks_a_mention_span_to_same_length_dots(self) -> None:
        # frob:tests src/frob/graph/dsl.py::mask_frob_mentions
        text = 'frob:quote(frob:waive WIRE001 reason="x")'
        masked = mask_frob_mentions(text)
        assert len(masked) == len(text)
        assert masked == "." * len(text)

    def test_leaves_unwrapped_text_untouched(self) -> None:
        # frob:tests src/frob/graph/dsl.py::mask_frob_mentions
        text = 'frob:waive WIRE001 reason="x"'
        assert mask_frob_mentions(text) == text

    def test_masks_only_the_wrapped_span_not_the_whole_line(self) -> None:
        # frob:tests src/frob/graph/dsl.py::mask_frob_mentions
        # T-1970 acceptance: an unescaped real directive on the SAME line
        # as an escaped mention must still be visible after masking.
        text = 'see frob:quote(follow_up="T-1956") -- frob:ticket T-1956'
        masked = mask_frob_mentions(text)
        assert "frob:ticket T-1956" in masked
        assert "follow_up" not in masked

    def test_idempotent(self) -> None:
        # frob:tests src/frob/graph/dsl.py::mask_frob_mentions
        text = 'frob:quote(frob:waive WIRE001 reason="x")'
        once = mask_frob_mentions(text)
        assert mask_frob_mentions(once) == once


class TestParseDirectivesMentionEscape:
    def test_escaped_waive_mention_does_not_produce_a_waive_edge_or_malformed(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # T-1970 acceptance: an escaped mention of frob:waive WIRE001 and
        # of follow_up="T-####" must not be parsed as a directive at all.
        src = (
            "def foo() -> None:\n"
            "    # discharged: frob:quote(frob:waive WIRE001 reason=\"x\" "
            'follow_up="T-1956") is no longer needed\n'
            "    pass\n"
        )
        parsed = parse_file(_write(tmp_path, "m.py", src)).danger_ok
        edges, malformed = parse_directives(parsed)
        assert edges == ()
        assert malformed == ()

    def test_unescaped_real_directive_on_the_same_line_still_parses(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # T-1970 acceptance: escaping one span must not weaken an
        # UNESCAPED real directive elsewhere on the same physical line.
        src = (
            "def foo() -> None:\n"
            "    pass\n"
            "\n"
            "def bar() -> None:\n"
            '    # frob:waive RULE-1 reason="real, unescaped, still live"\n'
            "    pass\n"
        )
        parsed = parse_file(_write(tmp_path, "m.py", src)).danger_ok
        edges, malformed = parse_directives(parsed)
        assert malformed == ()
        assert len(edges) == 1
        assert edges[0].kind == EdgeKind.WAIVE
        assert edges[0].target == "RULE-1"

    def test_escaped_mention_of_an_unknown_verb_produces_no_dsl001(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::parse_directives
        # The over-parse half of T-1970's own measured incident: a
        # reworded comment containing the literal substring
        # `frob:waive WIRE001` while DESCRIBING the waiver being removed
        # used to become a MalformedDirective (DSL001). Escaped, it must
        # not.
        src = (
            "def foo() -> None:\n"
            "    # removed: frob:quote(frob:waive WIRE001) was here\n"
            "    pass\n"
        )
        parsed = parse_file(_write(tmp_path, "m.py", src)).danger_ok
        _edges, malformed = parse_directives(parsed)
        assert malformed == ()


class TestMarkdownAnchorsMentionEscape:
    def test_escaped_describes_mention_produces_no_edge(self) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        text = (
            "# Heading\n\n"
            "Describing the syntax: "
            "frob:quote(<!-- frob:describes src/x.py::Y -->) is the shape.\n"
        )
        edges, malformed = markdown_anchors("doc.md", text)
        assert edges == ()
        assert malformed == ()

    def test_unescaped_directive_on_same_line_as_escaped_mention_still_parses(
        self,
    ) -> None:
        # frob:tests src/frob/graph/dsl.py::markdown_anchors
        text = (
            "# Heading\n\n"
            "<!-- frob:describes src/x.py::Y --> "
            "frob:quote(<!-- frob:describes src/z.py::W -->)\n"
        )
        edges, malformed = markdown_anchors("doc.md", text)
        assert malformed == ()
        assert len(edges) == 1
        assert edges[0].target == "src/x.py::Y"
