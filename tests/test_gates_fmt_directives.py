"""Tests for `frob fmt`'s directive canonicalization (T-0441,
docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441).

Covers: wrap (over-long single line splits), un-wrap (an over-split
directive that now fits joins back to one line), idempotency in both
directions, a property test that wrapping then folding a directive's text
back is always the identity, and a mutant of `_canonical_lines`' budget
math that a correct implementation must catch (TEST016).
"""

from __future__ import annotations

import string

from hypothesis import given
from hypothesis import strategies as st

from frob.gates._fmt_directives import (
    _canonical_lines,
    canonicalize_text,
    format_paths,
    marker_for,
    read_line_length,
)
from frob.graph.dsl import fold_comment_runs


def _fold_lines(physical: list[str], marker: str) -> str:
    """Strip `marker` + one leading space from each of `physical`, then fold
    via T-0286's own fold (`fold_comment_runs`) -- the exact mechanism
    `frob.graph.dsl.parse_directives` uses -- and return the resulting
    logical text. Used to assert the round-trip property: whatever
    `_canonical_lines` emits must fold back to the original input."""
    entries = []
    for i, raw in enumerate(physical):
        content = raw[len(marker) :]
        if content.startswith(" "):
            content = content[1:]
        entries.append((i, content, "", 0))
    folded = fold_comment_runs(entries)
    assert len(folded) == 1
    return folded[0][0]


class TestMarkerFor:
    """Language-suffix to line-comment-marker lookup."""

    def test_python_uses_hash(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestMarkerFor.test_python_uses_hash
        assert marker_for("src/frob/foo.py") == "#"

    def test_rust_uses_slash_slash(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestMarkerFor.test_rust_uses_slash_slash
        assert marker_for("src/lib.rs") == "//"

    def test_unsupported_suffix_is_none(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestMarkerFor.test_unsupported_suffix_is_none
        assert marker_for("README.md") is None


class TestReadLineLength:
    """Reads `[tool.ruff] line-length` from `pyproject.toml`, else 88."""

    def test_reads_configured_limit(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_fmt_directives.py::TestReadLineLength.test_reads_configured_limit
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
        assert read_line_length(tmp_path) == 100

    def test_missing_file_defaults_to_88(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_fmt_directives.py::TestReadLineLength.test_missing_file_defaults_to_88
        assert read_line_length(tmp_path) == 88

    def test_missing_ruff_section_defaults_to_88(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_fmt_directives.py::TestReadLineLength.test_missing_ruff_section_defaults_to_88
        (tmp_path / "pyproject.toml").write_text("[tool.other]\nx = 1\n")
        assert read_line_length(tmp_path) == 88


class TestCanonicalLinesRoundTrip:
    """`_canonical_lines(text) -> physical lines`, folded back, is the
    identity -- the core round-trip property T-0441's design demands."""

    def test_short_text_stays_one_line(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_short_text_stays_one_line
        lines = _canonical_lines("frob:ticket T-0441", marker="#", indent="", limit=88)
        assert lines == ["# frob:ticket T-0441"]

    def test_long_text_wraps_and_folds_back_identical(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_long_text_wraps_and_folds_back_identical
        text = (
            'frob:waive RULE-1 reason="this reason is intentionally long so '
            'it would overflow the ruff line-length limit and needs wrapping"'
        )
        lines = _canonical_lines(text, marker="#", indent="", limit=88)
        assert len(lines) > 1
        for line in lines:
            assert len(line) <= 88
        assert _fold_lines(lines, "#") == text

    @given(
        # MAJOR fix (reviewer): the alphabet must include backslashes and
        # quotes -- the exact character class the continuation marker
        # itself (a trailing "\") interacts with -- not just "safe"
        # word/attribute characters. Hand-verified (see the dedicated
        # backslash-focused tests below) and Hypothesis-verified here that
        # a body backslash mid-text always round-trips: `_canonical_lines`
        # appends exactly one "\" continuation marker per physical line,
        # and `fold_comment_runs` always strips exactly one trailing "\"
        # per line when folding, regardless of how many backslashes the
        # BODY itself contributes at that boundary -- net zero change, by
        # construction, so this holds for any number of body backslashes.
        st.text(
            alphabet=st.sampled_from(
                string.ascii_letters + string.digits + " _-=\"'\\"
            ),
            min_size=1,
            max_size=400,
        ).filter(lambda s: not s.strip().endswith("\\")),
        st.integers(min_value=20, max_value=120),
    )
    def test_wrap_then_fold_is_identity(self, body: str, limit: int) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_wrap_then_fold_is_identity
        text = f"frob:ticket {body}"
        lines = _canonical_lines(text, marker="#", indent="", limit=limit)
        assert _fold_lines(lines, "#") == text

    def test_backslash_at_exact_wrap_boundary_round_trips(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_backslash_at_exact_wrap_boundary_round_trips
        # A body backslash landing exactly where `_canonical_lines` would
        # cut -- so the emitted physical line ends in TWO backslashes (the
        # body's own, plus the appended continuation marker) -- must still
        # fold back to exactly one backslash at that position (T-0441 MAJOR
        # fix): fold always strips exactly one trailing "\", so append-one/
        # strip-one is a net no-op on however many the body contributed.
        text = 'frob:waive R reason="a\\\\b ' + ("y" * 40) + '"'
        lines = _canonical_lines(text, marker="#", indent="", limit=30)
        assert len(lines) > 1
        assert _fold_lines(lines, "#") == text

    def test_double_backslash_in_body_round_trips(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_double_backslash_in_body_round_trips
        text = 'frob:waive R reason="path\\\\\\\\to\\\\\\\\file ' + ("z" * 40) + '"'
        lines = _canonical_lines(text, marker="#", indent="", limit=30)
        assert _fold_lines(lines, "#") == text

    def test_indent_is_preserved_on_every_physical_line(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_indent_is_preserved_on_every_physical_line
        text = 'frob:waive R reason="' + ("x" * 100) + '"'
        lines = _canonical_lines(text, marker="#", indent="    ", limit=40)
        for line in lines:
            assert line.startswith("    #")


class TestCanonicalizeText:
    """`canonicalize_text`: file-level wrap/un-wrap of every `frob:` run."""

    def test_wraps_over_long_single_line_directive(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_wraps_over_long_single_line_directive
        src = (
            "def f():\n"
            '    # frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"\n'
            "    pass\n"
        )
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out != src
        for line in out.splitlines():
            assert len(line) <= 88
        # Re-parsing (folding) the wrapped comment lines back must recover
        # the original logical directive text exactly.
        comment_lines = [
            line.strip() for line in out.splitlines() if line.strip().startswith("#")
        ]
        entries = [
            (i, line[1:].lstrip(" "), "", 0) for i, line in enumerate(comment_lines)
        ]
        folded = fold_comment_runs(entries)
        assert len(folded) == 1
        assert folded[0][0] == (
            'frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"'
        )

    def test_joins_over_split_directive_that_now_fits(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_joins_over_split_directive_that_now_fits
        src = (
            'def f():\n    # frob:waive RULE-1 reason="short \\\n    # now"\n    pass\n'
        )
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out == (
            'def f():\n    # frob:waive RULE-1 reason="short now"\n    pass\n'
        )

    def test_three_line_continuation_that_fits_collapses_to_one(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_three_line_continuation_that_fits_collapses_to_one
        src = '# frob:waive R reason="a \\\n# b \\\n# c"\n'
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out == '# frob:waive R reason="a b c"\n'

    def test_re_wraps_to_minimal_split_when_only_first_line_over_long(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_re_wraps_to_minimal_split_when_only_first_line_over_long
        long_reason = "x" * 60
        src = f'# frob:waive R reason="{long_reason} short \\\n# tail"\n'
        out = canonicalize_text(src, path="a.py", limit=88)
        for line in out.splitlines():
            assert len(line) <= 88
        comment_lines = [
            line[1:].lstrip(" ") for line in out.splitlines() if line.startswith("#")
        ]
        entries = [(i, line, "", 0) for i, line in enumerate(comment_lines)]
        folded = fold_comment_runs(entries)
        assert folded[0][0] == f'frob:waive R reason="{long_reason} short tail"'

    def test_idempotent_on_already_canonical_text(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_idempotent_on_already_canonical_text
        src = (
            "def f():\n"
            '    # frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"\n'
            "    pass\n"
        )
        once = canonicalize_text(src, path="a.py", limit=88)
        twice = canonicalize_text(once, path="a.py", limit=88)
        assert once == twice

    def test_non_directive_comments_are_untouched(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_non_directive_comments_are_untouched
        src = "# just a very ordinary long comment that has nothing to do with frob at all, really\n"
        out = canonicalize_text(src, path="a.py", limit=40)
        assert out == src

    def test_unsupported_language_returns_text_unchanged(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_unsupported_language_returns_text_unchanged
        src = "-- frob:ticket T-0441\n"
        assert canonicalize_text(src, path="a.sql", limit=88) == src

    def test_rust_double_slash_marker_round_trips(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_rust_double_slash_marker_round_trips
        src = (
            '// frob:waive RULE-1 reason="this reason is intentionally long so '
            'it overflows the line-length limit and must be wrapped"\n'
        )
        out = canonicalize_text(src, path="a.rs", limit=88)
        assert out != src
        for line in out.splitlines():
            assert len(line) <= 88
        comment_lines = [
            line.strip()[2:].lstrip(" ")
            for line in out.splitlines()
            if line.strip().startswith("//")
        ]
        entries = [(i, line, "", 0) for i, line in enumerate(comment_lines)]
        folded = fold_comment_runs(entries)
        assert folded[0][0] == (
            'frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"'
        )


class TestCrlfPreservation:
    """T-0441 CRITICAL fix: a CRLF source file's line endings must survive
    `frob fmt` untouched on every line this function does not rewrite --
    only the over-long directive run's own physical lines may change."""

    def test_canonicalize_text_preserves_crlf_on_untouched_lines(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCrlfPreservation.test_canonicalize_text_preserves_crlf_on_untouched_lines
        src = (
            "fn f() {\r\n"
            '    // frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"\r\n'
            "    do_thing();\r\n"
            "}\r\n"
        )
        out = canonicalize_text(src, path="a.rs", limit=88)
        assert out != src
        lines = out.split("\n")
        # Every physical line -- including the newly wrapped directive run
        # -- still ends in "\r" (CRLF preserved); no bare "\n"-only line.
        for line in lines[:-1]:
            assert line.endswith("\r"), f"{line!r} lost its CRLF terminator"
        # Untouched code lines are byte-for-byte identical to the source.
        assert "fn f() {\r\n" in out
        assert "    do_thing();\r\n" in out
        assert out.endswith("}\r\n")
        # The directive itself still folds back to the exact original text.
        comment_lines = [
            line.strip()[2:].lstrip(" ").rstrip("\r")
            for line in lines
            if line.strip().startswith("//")
        ]
        entries = [(i, line, "", 0) for i, line in enumerate(comment_lines)]
        folded = fold_comment_runs(entries)
        assert folded[0][0] == (
            'frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"'
        )

    def test_canonicalize_text_is_a_no_op_on_second_pass(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCrlfPreservation.test_canonicalize_text_is_a_no_op_on_second_pass
        src = (
            "fn f() {\r\n"
            '    // frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"\r\n'
            "    do_thing();\r\n"
            "}\r\n"
        )
        once = canonicalize_text(src, path="a.rs", limit=88)
        twice = canonicalize_text(once, path="a.rs", limit=88)
        assert once == twice

    def test_format_paths_preserves_crlf_end_to_end(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_fmt_directives.py::TestCrlfPreservation.test_format_paths_preserves_crlf_end_to_end
        target = tmp_path / "a.rs"
        original = (
            "fn f() {\r\n"
            '    // frob:waive RULE-1 reason="this reason is intentionally long '
            'so it overflows the line-length limit and must be wrapped"\r\n'
            "    do_thing();\r\n"
            "}\r\n"
        )
        with open(target, "wb") as fh:
            fh.write(original.encode("utf-8"))

        report = format_paths(tmp_path, check_only=False, limit=88)
        assert [c.path for c in report.changes] == ["a.rs"]

        with open(target, "rb") as fh:
            raw = fh.read()
        assert b"\r\n" in raw
        assert b"do_thing();\r\n" in raw
        assert b"fn f() {\r\n" in raw
        # No line-ending got silently flattened to a bare "\n": every
        # newline byte in the rewritten file is still preceded by "\r".
        assert raw.count(b"\n") == raw.count(b"\r\n")

        # A second pass over the already-canonical, still-CRLF file is a
        # true no-op at the byte level (idempotent, not just line-count
        # stable) -- `format_paths` must report zero further changes.
        report2 = format_paths(tmp_path, check_only=True, limit=88)
        assert report2.changes == ()
        with open(target, "rb") as fh:
            raw2 = fh.read()
        assert raw2 == raw


class TestFormatPaths:
    """`format_paths`: file-tree wrapper, check-only vs. write mode."""

    def test_check_mode_reports_without_writing(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_fmt_directives.py::TestFormatPaths.test_check_mode_reports_without_writing
        target = tmp_path / "a.py"
        original = (
            '# frob:waive R reason="this reason is intentionally long so '
            'it overflows the line-length limit and must be wrapped"\n'
        )
        target.write_text(original)
        report = format_paths(tmp_path, check_only=True, limit=88)
        assert [c.path for c in report.changes] == ["a.py"]
        assert target.read_text() == original

    def test_write_mode_rewrites_file(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_fmt_directives.py::TestFormatPaths.test_write_mode_rewrites_file
        target = tmp_path / "a.py"
        original = (
            '# frob:waive R reason="this reason is intentionally long so '
            'it overflows the line-length limit and must be wrapped"\n'
        )
        target.write_text(original)
        report = format_paths(tmp_path, check_only=False, limit=88)
        assert [c.path for c in report.changes] == ["a.py"]
        rewritten = target.read_text()
        assert rewritten != original
        for line in rewritten.splitlines():
            assert len(line) <= 88

    def test_already_canonical_file_reports_no_changes(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests tests/test_gates_fmt_directives.py::TestFormatPaths.test_already_canonical_file_reports_no_changes
        target = tmp_path / "a.py"
        target.write_text("# frob:ticket T-0441\n")
        report = format_paths(tmp_path, check_only=True, limit=88)
        assert report.changes == ()


class TestCanonicalLinesMutantKiller:
    """A mutant of `_canonical_lines`' budget math (off-by-one that leaves
    no room for the trailing backslash) produces an over-length physical
    line; this test fails against that mutant and passes against the real
    implementation (TEST016)."""

    def test_every_physical_line_is_strictly_within_limit(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller.test_every_physical_line_is_strictly_within_limit
        text = 'frob:waive R reason="' + ("word " * 40).strip() + '"'
        limit = 50
        lines = _canonical_lines(text, marker="#", indent="", limit=limit)
        assert len(lines) > 1
        for line in lines:
            # A mutant that computes budget as `room` instead of `room - 1`
            # (forgetting to reserve a column for the trailing "\") emits a
            # line one column over `limit` here -- this assertion catches it.
            assert len(line) <= limit, f"{line!r} exceeds limit={limit}"
        assert _fold_lines(lines, "#") == text

    def test_no_breakable_space_still_stays_within_limit(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller.test_no_breakable_space_still_stays_within_limit
        # A single unbroken run (no spaces) forces the fallback "cut at the
        # budget boundary verbatim" branch -- this is the branch a
        # room-vs-room-minus-1 off-by-one mutant overflows by exactly one
        # column, where the space-seeking `rfind` branch above usually
        # masks the bug by finding an earlier, safe cut point instead.
        text = "frob:ticket " + ("x" * 200)
        limit = 50
        lines = _canonical_lines(text, marker="#", indent="", limit=limit)
        assert len(lines) > 1
        for line in lines:
            assert len(line) <= limit, f"{line!r} exceeds limit={limit}"
        assert _fold_lines(lines, "#") == text


# frob:ticket T-0984
class TestBoundaryOffByOneT0984:
    """T-0984 regression: T-0972 found `_canonical_lines` wrapping to 89
    columns (one over an 88-char limit) when a repo-wide `frob fmt` run
    touched ~180 out-of-scope files. Root cause: `rfind(" ", 0, budget +
    1)` let a space AT index `budget` itself match, and keeping that space
    on the earlier line (`remaining[: cut + 1]`) produced a `head` of
    length `budget + 1` -- one column over budget, hence one over `limit`.
    These fixtures pin the exact at-limit / one-under / one-over boundary
    the incident was found at, plus the specific space-at-budget-boundary
    shape that triggered the overflow."""

    def test_space_exactly_at_budget_boundary_does_not_overflow(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_space_exactly_at_budget_boundary_does_not_overflow
        # prefix = "# " (len 2), limit=88 -> room=86, budget=85. A space at
        # index 85 (0-indexed) of `remaining` is the exact boundary the
        # buggy `rfind(" ", 0, budget + 1)` would match and misplace.
        text = ("x" * 85) + " " + ("y" * 50)
        lines = _canonical_lines(text, marker="#", indent="", limit=88)
        assert len(lines) > 1
        for line in lines:
            assert len(line) <= 88, f"{line!r} exceeds limit=88"
        assert _fold_lines(lines, "#") == text

    def test_directive_line_at_exact_limit_is_byte_identical(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_directive_line_at_exact_limit_is_byte_identical
        # A single-line directive whose total physical width is EXACTLY the
        # configured limit must round-trip through `canonicalize_text`
        # completely untouched -- this is the "at-limit" fixture in the
        # ticket's at-limit/one-under/one-over trio.
        limit = 88
        prefix_len = len("# ")
        text = "frob:ticket " + ("x" * (limit - prefix_len - len("frob:ticket ")))
        src = f"# {text}\n"
        assert len(src.splitlines()[0]) == limit
        out = canonicalize_text(src, path="a.py", limit=limit)
        assert out == src

    def test_directive_line_one_under_limit_is_byte_identical(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_directive_line_one_under_limit_is_byte_identical
        limit = 88
        prefix_len = len("# ")
        text = "frob:ticket " + ("x" * (limit - prefix_len - len("frob:ticket ") - 1))
        src = f"# {text}\n"
        assert len(src.splitlines()[0]) == limit - 1
        out = canonicalize_text(src, path="a.py", limit=limit)
        assert out == src

    def test_directive_line_one_over_limit_wraps_and_stays_in_bounds(self) -> None:
        # frob:tests tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_directive_line_one_over_limit_wraps_and_stays_in_bounds
        limit = 88
        prefix_len = len("# ")
        text = "frob:ticket " + ("x" * (limit - prefix_len - len("frob:ticket ") + 1))
        src = f"# {text}\n"
        assert len(src.splitlines()[0]) == limit + 1
        out = canonicalize_text(src, path="a.py", limit=limit)
        assert out != src
        for line in out.splitlines():
            assert len(line) <= limit, f"{line!r} exceeds limit={limit}"
        comment_lines = [
            line[1:].lstrip(" ") for line in out.splitlines() if line.startswith("#")
        ]
        entries = [(i, line, "", 0) for i, line in enumerate(comment_lines)]
        folded = fold_comment_runs(entries)
        assert folded[0][0] == text
