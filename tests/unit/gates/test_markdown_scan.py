"""Tests for `frob.gates._markdown_scan.strip_code_spans` (T-1700): the
shared code-span-blanking helper DOC011 and TICK006 both scan prose
through, extracted so neither rule risks a second, independently-
drifting copy of the same regex pair.
"""

from __future__ import annotations

from frob.gates._markdown_scan import strip_code_spans


class TestStripCodeSpans:
    """`strip_code_spans`: blank fenced/inline code, preserve everything
    else (including newline count, so line numbers stay correct)."""

    def test_single_backtick_span_is_blanked(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_single_backtick_span_is_blanked  # noqa: E501
        text = "See `T-0001` for background."
        stripped = strip_code_spans(text)
        assert "T-0001" not in stripped
        assert len(stripped) == len(text)

    def test_double_backtick_span_is_blanked(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_double_backtick_span_is_blanked  # noqa: E501
        # T-1700's own root cause: a single-backtick-only regex silently
        # fails to match a DOUBLE-backtick-delimited span (the CommonMark
        # escape for a span whose own content needs a literal backtick,
        # or just a writer's habit) as one span at all, leaving its
        # content completely unblanked.
        text = "Example: `` `Filed: T-0104` `` illustrates the syntax."
        stripped = strip_code_spans(text)
        assert "T-0104" not in stripped
        assert "Filed" not in stripped

    def test_triple_backtick_span_is_blanked(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_triple_backtick_span_is_blanked  # noqa: E501
        # A backtick RUN of any length closes with the next run of the
        # SAME length, per CommonMark -- not just one or two.
        text = 'See ``` `waive ... ticket "T-9999";` ``` for the shape.'
        stripped = strip_code_spans(text)
        assert "T-9999" not in stripped

    def test_run_length_must_match_to_close(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_run_length_must_match_to_close  # noqa: E501
        # CommonMark: a span opened by a run of N backticks closes with
        # the NEXT run of exactly N backticks -- a shorter or longer run
        # inside the content does not close it early or leave it open too
        # long. A single backtick inside double-backtick-delimited
        # content must not be mistaken for the closing pair.
        text = "`` a single ` backtick inside T-0005 stays hidden ``"
        stripped = strip_code_spans(text)
        assert "T-0005" not in stripped

    def test_fenced_code_block_is_blanked(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_fenced_code_block_is_blanked  # noqa: E501
        text = "before\n```\nfrob ticket show T-9999\n```\nafter"
        stripped = strip_code_spans(text)
        assert "T-9999" not in stripped
        assert "before" in stripped
        assert "after" in stripped

    # frob:waive PII012 reason="'token' here means a single lexical unit of markdown (a wrapped inline code span treated as one unit), not a credential"  # noqa: E501
    def test_line_wrapped_inline_span_is_blanked_as_one_token(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_line_wrapped_inline_span_is_blanked_as_one_token  # noqa: E501
        text = "`frob quality \n bind` is one token"
        stripped = strip_code_spans(text)
        assert "frob quality" not in stripped
        assert "bind" not in stripped

    def test_blank_line_is_not_treated_as_inside_a_span(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_blank_line_is_not_treated_as_inside_a_span  # noqa: E501
        # Two consecutive newlines are a real paragraph break -- an
        # opening backtick before one and a closing backtick after are
        # two unrelated stray characters, never a genuine wrapped span.
        text = "start `here\n\nT-0002 stays real prose` end"
        stripped = strip_code_spans(text)
        assert "T-0002" in stripped

    def test_newline_count_preserved(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_newline_count_preserved  # noqa: E501
        text = "line one\n`code span`\nline three\n"
        stripped = strip_code_spans(text)
        assert text.count("\n") == stripped.count("\n")

    def test_prose_with_no_code_spans_is_unchanged(self) -> None:
        # frob:tests tests/unit/gates/test_markdown_scan.py::TestStripCodeSpans.test_prose_with_no_code_spans_is_unchanged  # noqa: E501
        text = "Ordinary prose mentioning T-0003 with no backticks at all."
        assert strip_code_spans(text) == text
