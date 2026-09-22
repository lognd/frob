"""Tests for `frob fmt`'s directive canonicalization (T-0441,
docs/modules/gates.md#frob-fmt-directive-canonicalization-t-0441).

Covers: wrap (over-long single line splits), un-wrap (an over-split
directive that now fits joins back to one line), idempotency in both
directions, a property test that wrapping then folding a directive's text
back is always the identity, and a mutant of `_canonical_lines`' budget
math that a correct implementation must catch (TEST016).
"""

from __future__ import annotations

import os
import string
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from frob.excludes import iter_files
from frob.gates._fmt_directives import (
    _canonical_lines,
    _write_formatted,
    canonicalize_text,
    format_paths,
    marker_for,
    read_line_length,
    resolve_line_length,
)
from frob.graph.dsl import fold_comment_runs


def _fold_lines_real_extractor(physical: list[str], marker: str) -> str:
    """Like `_fold_lines`, but strips each physical line's marker prefix
    with a FULL `.strip()` (both leading and trailing whitespace), matching
    `frob.lang._common._strip_comment_delims`'s actual per-line stripping
    -- not `_fold_lines`'s own lenient one-leading-space strip.

    T-0991: `_fold_lines`'s lenient strip is why the original T-0984-era
    property test never caught the boundary-space bug -- it only removed
    ONE leading space per continuation line, which happened to be forgiving
    enough to mask a case where the real parser's full `.strip()` eats a
    boundary space entirely and silently concatenates two tokens. Any new
    round-trip assertion against the REAL directive-parsing path must go
    through this stricter helper instead."""
    entries = []
    for i, raw in enumerate(physical):
        content = raw[len(marker) :].strip()
        entries.append((i, content, "", 0))
    folded = fold_comment_runs(entries)
    assert len(folded) == 1
    return folded[0][0]


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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestMarkerFor.test_python_uses_hash
        assert marker_for("src/frob/foo.py") == "#"

    def test_rust_uses_slash_slash(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestMarkerFor.test_rust_uses_slash_slash
        assert marker_for("src/lib.rs") == "//"

    def test_unsupported_suffix_is_none(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestMarkerFor.test_unsupported_suffix_is_none  # noqa: E501
        assert marker_for("README.md") is None


class TestReadLineLength:
    """Reads `[tool.ruff] line-length` from `pyproject.toml`, else 88."""

    def test_reads_configured_limit(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestReadLineLength.test_reads_configured_limit  # noqa: E501
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
        assert read_line_length(tmp_path) == 100

    def test_missing_file_defaults_to_88(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestReadLineLength.test_missing_file_defaults_to_88  # noqa: E501
        assert read_line_length(tmp_path) == 88

    def test_missing_ruff_section_defaults_to_88(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestReadLineLength.test_missing_ruff_section_defaults_to_88  # noqa: E501
        (tmp_path / "pyproject.toml").write_text("[tool.other]\nx = 1\n")
        assert read_line_length(tmp_path) == 88


class TestResolveLineLength:
    """T-1606: each supported non-Python language resolves its OWN
    formatter's width from that formatter's own config, never ruff's."""

    def test_python_uses_ruff_config(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_python_uses_ruff_config  # noqa: E501
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
        assert resolve_line_length(tmp_path / "m.py", tmp_path) == 100

    def test_rust_uses_rustfmt_toml(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_rust_uses_rustfmt_toml  # noqa: E501
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
        (tmp_path / "rustfmt.toml").write_text("max_width = 120\n")
        assert resolve_line_length(tmp_path / "src" / "lib.rs", tmp_path) == 120

    def test_rust_falls_back_to_tool_default(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_rust_falls_back_to_tool_default  # noqa: E501
        assert resolve_line_length(tmp_path / "lib.rs", tmp_path) == 100

    def test_prettier_uses_prettierrc(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_prettier_uses_prettierrc  # noqa: E501
        (tmp_path / ".prettierrc").write_text('{"printWidth": 120}')
        assert resolve_line_length(tmp_path / "a.ts", tmp_path) == 120

    def test_prettier_uses_package_json_key(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_prettier_uses_package_json_key  # noqa: E501
        (tmp_path / "package.json").write_text(
            '{"name": "x", "prettier": {"printWidth": 110}}'
        )
        assert resolve_line_length(tmp_path / "a.js", tmp_path) == 110

    def test_prettier_falls_back_to_tool_default(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_prettier_falls_back_to_tool_default  # noqa: E501
        assert resolve_line_length(tmp_path / "a.tsx", tmp_path) == 80

    def test_clang_format_uses_config(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_clang_format_uses_config  # noqa: E501
        (tmp_path / ".clang-format").write_text("ColumnLimit: 120\n")
        assert resolve_line_length(tmp_path / "a.cpp", tmp_path) == 120

    def test_clang_format_falls_back_to_tool_default(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_clang_format_falls_back_to_tool_default  # noqa: E501
        assert resolve_line_length(tmp_path / "a.c", tmp_path) == 80

    def test_nearest_config_wins_over_root_config(self, tmp_path) -> None:  # noqa: ANN001
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_nearest_config_wins_over_root_config  # noqa: E501
        (tmp_path / "rustfmt.toml").write_text("max_width = 100\n")
        pkg = tmp_path / "crates" / "sub"
        pkg.mkdir(parents=True)
        (pkg / "rustfmt.toml").write_text("max_width = 60\n")
        assert resolve_line_length(pkg / "lib.rs", tmp_path) == 60

    def test_unregistered_suffix_falls_back_to_ruff_derived_default(
        self, tmp_path
    ) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_unregistered_suffix_falls_back_to_ruff_derived_default  # noqa: E501
        # `.strata` has no dedicated formatter of its own (T-1606 design
        # decision) -- it keeps the pre-T-1606 ruff-derived behavior.
        (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 100\n")
        assert resolve_line_length(tmp_path / "a.strata", tmp_path) == 100

    def test_no_limit_language_never_wraps(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestResolveLineLength.test_no_limit_language_never_wraps  # noqa: E501
        # T-1606: `limit=None` is the first-class "this formatter has no
        # width concept" answer (the contract a future Go/Zig/Bash adapter
        # would return from `resolve_line_length`) -- proven at the
        # `canonicalize_text` level, since none of today's `_MARKERS`
        # suffixes reach it via `resolve_line_length` itself yet.
        text = '# frob:waive RULE001 reason="' + ("x" * 300) + '"\n'
        rewritten = canonicalize_text(text, path="a.py", limit=None)
        assert rewritten == text
        assert "\\\n" not in rewritten


class TestCanonicalLinesRoundTrip:
    """`_canonical_lines(text) -> physical lines`, folded back, is the
    identity -- the core round-trip property T-0441's design demands."""

    def test_short_text_stays_one_line(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_short_text_stays_one_line  # noqa: E501
        lines = _canonical_lines("frob:ticket T-0441", marker="#", indent="", limit=88)
        assert lines == ["# frob:ticket T-0441"]

    def test_long_text_wraps_and_folds_back_identical(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_long_text_wraps_and_folds_back_identical  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_wrap_then_fold_is_identity  # noqa: E501
        # T-4475: when the FINAL segment is an unbreakable token wider than
        # the wrap budget, its physical line carries an auto-appended
        # `# noqa: E501` (marker == "#" here) -- folding then reproduces
        # `text` with that suffix appended, not `text` alone.
        text = f"frob:ticket {body}"
        lines = _canonical_lines(text, marker="#", indent="", limit=limit)
        folded = _fold_lines(lines, "#")
        assert folded in (text, text + "  # noqa: E501")

    def test_backslash_at_exact_wrap_boundary_round_trips(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_backslash_at_exact_wrap_boundary_round_trips  # noqa: E501
        # A body backslash landing exactly where `_canonical_lines` would
        # cut -- so the emitted physical line ends in TWO backslashes (the
        # body's own, plus the appended continuation marker) -- must still
        # fold back to exactly one backslash at that position (T-0441 MAJOR
        # fix): fold always strips exactly one trailing "\", so append-one/
        # strip-one is a net no-op on however many the body contributed.
        # The trailing `"y" * 40` is itself an unbreakable token wider than
        # the limit=30 budget, so its own final line carries T-4475's
        # auto-appended `# noqa: E501` -- folding reproduces `text` plus
        # that suffix, not `text` alone (only the FULL `canonicalize_text`
        # pipeline, via `_rewrite_directive_run`'s pre-existing noqa
        # short-circuit, makes the round trip a strict no-suffix identity
        # on a SECOND pass).
        text = 'frob:waive R reason="a\\\\b ' + ("y" * 40) + '"'
        lines = _canonical_lines(text, marker="#", indent="", limit=30)
        assert len(lines) > 1
        assert _fold_lines(lines, "#") == text + "  # noqa: E501"

    def test_double_backslash_in_body_round_trips(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_double_backslash_in_body_round_trips  # noqa: E501
        # Trailing "z" * 40 is unbreakable and wider than limit=30 -- same
        # T-4475 auto-noqa shape as the test immediately above.
        text = 'frob:waive R reason="path\\\\\\\\to\\\\\\\\file ' + ("z" * 40) + '"'
        lines = _canonical_lines(text, marker="#", indent="", limit=30)
        assert _fold_lines(lines, "#") == text + "  # noqa: E501"

    def test_indent_is_preserved_on_every_physical_line(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesRoundTrip.test_indent_is_preserved_on_every_physical_line  # noqa: E501
        text = 'frob:waive R reason="' + ("x" * 100) + '"'
        lines = _canonical_lines(text, marker="#", indent="    ", limit=40)
        for line in lines:
            assert line.startswith("    #")


class TestCanonicalizeText:
    """`canonicalize_text`: file-level wrap/un-wrap of every `frob:` run."""

    def test_wraps_over_long_single_line_directive(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_wraps_over_long_single_line_directive  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_joins_over_split_directive_that_now_fits  # noqa: E501
        src = (
            'def f():\n    # frob:waive RULE-1 reason="short \\\n    # now"\n    pass\n'
        )
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out == (
            'def f():\n    # frob:waive RULE-1 reason="short now"\n    pass\n'
        )

    def test_three_line_continuation_that_fits_collapses_to_one(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_three_line_continuation_that_fits_collapses_to_one  # noqa: E501
        src = '# frob:waive R reason="a \\\n# b \\\n# c"\n'
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out == '# frob:waive R reason="a b c"\n'

    def test_re_wraps_to_minimal_split_when_only_first_line_over_long(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_re_wraps_to_minimal_split_when_only_first_line_over_long  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_idempotent_on_already_canonical_text  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_non_directive_comments_are_untouched  # noqa: E501
        src = "# just a very ordinary long comment that has nothing to do with frob at all, really\n"
        out = canonicalize_text(src, path="a.py", limit=40)
        assert out == src

    def test_unsupported_language_returns_text_unchanged(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_unsupported_language_returns_text_unchanged  # noqa: E501
        src = "-- frob:ticket T-0441\n"
        assert canonicalize_text(src, path="a.sql", limit=88) == src

    def test_rust_double_slash_marker_round_trips(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalizeText.test_rust_double_slash_marker_round_trips  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCrlfPreservation.test_canonicalize_text_preserves_crlf_on_untouched_lines  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCrlfPreservation.test_canonicalize_text_is_a_no_op_on_second_pass  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCrlfPreservation.test_format_paths_preserves_crlf_end_to_end  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestFormatPaths.test_check_mode_reports_without_writing  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestFormatPaths.test_write_mode_rewrites_file  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestFormatPaths.test_already_canonical_file_reports_no_changes  # noqa: E501
        target = tmp_path / "a.py"
        target.write_text("# frob:ticket T-0441\n")
        report = format_paths(tmp_path, check_only=True, limit=88)
        assert report.changes == ()

    def test_broad_path_formats_source_but_leaves_strata_fixtures_untouched(
        self, tmp_path: Path
    ) -> None:
        """T-2298 acceptance [0]: a broad `frob fmt` path formats genuinely
        unformatted source AND leaves a `tests/**/*.strata` fixture
        byte-identical -- the real incident (49 unrelated fixture files
        rewritten by a broad path) with a positive control (source still
        gets formatted, so this is not "fmt stopped working"). Must FAIL
        against pre-fix main."""
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestFormatPaths.test_broad_path_formats_source_but_leaves_strata_fixtures_untouched  # noqa: E501
        source = tmp_path / "a.py"
        unformatted = (
            '# frob:waive R reason="this reason is intentionally long so '
            'it overflows the line-length limit and must be wrapped"\n'
        )
        source.write_text(unformatted)

        fixture = tmp_path / "tests" / "fixtures" / "corpus.strata"
        fixture.parent.mkdir(parents=True)
        fixture_original = (
            '// frob:waive R reason="this reason is also intentionally '
            'long so it would overflow the line-length limit and wrap"\n'
        )
        fixture.write_text(fixture_original)

        report = format_paths(tmp_path, check_only=False, limit=88)

        assert source.read_text() != unformatted, "source should be formatted"
        assert fixture.read_text() == fixture_original, (
            "fixture must stay byte-identical"
        )
        assert "a.py" in [c.path for c in report.changes]
        assert "tests/fixtures/corpus.strata" not in [c.path for c in report.changes]

    def test_include_test_corpora_opts_back_in(self, tmp_path: Path) -> None:
        """T-2298: `include_test_corpora=True` formats a fixture file
        explicitly opted into -- the exclusion is a default, not a hard
        block."""
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestFormatPaths.test_include_test_corpora_opts_back_in  # noqa: E501
        fixture = tmp_path / "tests" / "fixtures" / "corpus.strata"
        fixture.parent.mkdir(parents=True)
        fixture_original = (
            '// frob:waive R reason="this reason is also intentionally '
            'long so it would overflow the line-length limit and wrap"\n'
        )
        fixture.write_text(fixture_original)

        report = format_paths(
            tmp_path, check_only=False, limit=88, include_test_corpora=True
        )
        assert "tests/fixtures/corpus.strata" in [c.path for c in report.changes]
        assert fixture.read_text() != fixture_original

    def test_explicit_single_fixture_path_is_still_formatted(
        self, tmp_path: Path
    ) -> None:
        """T-2298: naming a fixture file EXPLICITLY as the target (not
        reached via a broad walk) is a deliberate, scoped request and is
        still formatted -- the exclusion only applies to a broad path's
        expanded walk, matching `_land_cmd.py`'s own touched-file scoping
        (T-1404), which calls `format_paths` per-file on the ticket's real
        touched set."""
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestFormatPaths.test_explicit_single_fixture_path_is_still_formatted  # noqa: E501
        fixture = tmp_path / "tests" / "fixtures" / "corpus.strata"
        fixture.parent.mkdir(parents=True)
        fixture_original = (
            '// frob:waive R reason="this reason is also intentionally '
            'long so it would overflow the line-length limit and wrap"\n'
        )
        fixture.write_text(fixture_original)

        report = format_paths(fixture, check_only=False, limit=88)
        assert report.changes != ()
        assert fixture.read_text() != fixture_original


# frob:ticket T-1359
class TestWriteFormattedCrashSafety:
    """T-1359: `_write_formatted` (FMT001's write half) rewrites via a temp
    file + fsync + `os.replace` instead of a bare in-place `open(..., "w")`
    -- a process killed mid-rename must leave the ORIGINAL file intact
    rather than truncated (the T-1338 hazard class T-1348 already closed
    for `frob.gates._fix_engine`)."""

    def test_leaves_original_on_replace_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestWriteFormattedCrashSafety.test_leaves_original_on_replace_failure  # noqa: E501
        target = tmp_path / "a.py"
        original = "original\n"
        target.write_text(original, encoding="utf-8")

        def _boom(src: str, dst: str) -> None:
            raise OSError("simulated crash mid-rename")

        monkeypatch.setattr(os, "replace", _boom)
        with pytest.raises(OSError, match="simulated crash mid-rename"):
            _write_formatted(target, "rewritten\n")

        assert target.read_text(encoding="utf-8") == original
        leftovers = [p for p in tmp_path.iterdir() if p.name != "a.py"]
        assert leftovers == [], f"a partial/temp file leaked: {leftovers}"

    def test_preserves_crlf_newline(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestWriteFormattedCrashSafety.test_preserves_crlf_newline  # noqa: E501
        target = tmp_path / "a.py"
        _write_formatted(target, "line one\r\nline two\r\n")
        with open(target, encoding="utf-8", newline="") as fh:
            assert fh.read() == "line one\r\nline two\r\n"


class TestCanonicalLinesMutantKiller:
    """A mutant of `_canonical_lines`' budget math (off-by-one that leaves
    no room for the trailing backslash) produces an over-length physical
    line; this test fails against that mutant and passes against the real
    implementation (TEST016)."""

    def test_every_physical_line_is_strictly_within_limit(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller.test_every_physical_line_is_strictly_within_limit  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestCanonicalLinesMutantKiller.test_no_breakable_space_still_stays_within_limit  # noqa: E501
        # T-0441's original name kept verbatim (T-4179: T-0441's own
        # archived Done report cites this exact node id as evidence;
        # renaming it orphans that citation -- COV003) even though the
        # invariant it proves changed shape. A single unbroken run (no
        # spaces) wider than the wrap budget used to force a "cut at the
        # budget boundary verbatim" fallback that could land mid-token
        # (T-4179: exactly the pytest-node-id-split incident). The
        # contract is now "never split a token" -- the unbreakable run is
        # emitted whole, on its own over-`limit` line, rather than
        # fragmented across a `\\` continuation. Only the FIRST physical
        # line (the short leading word) still literally "stays within
        # limit"; the second line's own over-`limit` shape is exactly
        # what T-4179 intentionally introduces, asserted below.
        text = "frob:ticket " + ("x" * 200)
        limit = 50
        lines = _canonical_lines(text, marker="#", indent="", limit=limit)
        assert len(lines) == 2
        # The leading word wraps normally, within budget.
        assert len(lines[0]) <= limit, f"{lines[0]!r} exceeds limit={limit}"
        # The 200-char unbreakable run is intact -- not split across any
        # further physical line -- even though its line runs over `limit`.
        # T-4475: marker == "#" (Python) means this over-limit line also
        # gets an auto-appended `# noqa: E501` (ruff E501 suppression), so
        # the token itself sits just BEFORE that suffix, not at the very
        # end of the line.
        assert "x" * 200 in lines[1]
        assert lines[1].endswith("  # noqa: E501")
        assert "\\" not in lines[1]
        assert _fold_lines(lines, "#") == text + "  # noqa: E501"


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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_space_exactly_at_budget_boundary_does_not_overflow  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_directive_line_at_exact_limit_is_byte_identical  # noqa: E501
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
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_directive_line_one_under_limit_is_byte_identical  # noqa: E501
        limit = 88
        prefix_len = len("# ")
        text = "frob:ticket " + ("x" * (limit - prefix_len - len("frob:ticket ") - 1))
        src = f"# {text}\n"
        assert len(src.splitlines()[0]) == limit - 1
        out = canonicalize_text(src, path="a.py", limit=limit)
        assert out == src

    def test_directive_line_one_over_limit_wraps_and_stays_in_bounds(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestBoundaryOffByOneT0984.test_directive_line_one_over_limit_wraps_and_stays_in_bounds  # noqa: E501
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


class TestNoqaSuffixPragmaT0985:
    """T-0985: a `frob:` directive line ending in `# noqa`/`# noqa: CODE`
    is a deliberate escape hatch for an unwrappable single token (e.g. a
    long dotted pytest node id) -- `canonicalize_text` must leave it byte-
    identical rather than force-wrapping it."""

    def test_over_long_single_line_with_noqa_e501_is_byte_identical(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985.test_over_long_single_line_with_noqa_e501_is_byte_identical  # noqa: E501
        src = (
            "def f():\n"
            "    # frob:tests tests/some/very/long/dotted/module/path/test_thing.py"
            "::TestClassName.test_a_very_long_method_name_that_cannot_be_wrapped"
            "  # noqa: E501\n"
            "    pass\n"
        )
        assert len(src.splitlines()[1]) > 88
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out == src

    def test_over_long_single_line_with_bare_noqa_is_byte_identical(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985.test_over_long_single_line_with_bare_noqa_is_byte_identical  # noqa: E501
        src = '    # frob:waive RULE-1 reason="' + ("x" * 80) + '"  # noqa\n'
        assert len(src.splitlines()[0]) > 88
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out == src

    def test_over_long_line_without_noqa_still_wraps(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestNoqaSuffixPragmaT0985.test_over_long_line_without_noqa_still_wraps  # noqa: E501
        # Control case: the same over-long content WITHOUT the trailing
        # noqa pragma is still wrapped as usual -- the pragma, not mere
        # length, is what suppresses the rewrap. The `reason="..."` value
        # here is itself one unbreakable 80-char token, so the physical
        # line carrying it stays over `limit` by design (T-4179: never
        # split a token to force it under width) -- the earlier
        # `frob:waive RULE-1` words still wrap onto their own line(s).
        # T-4475: the trailing `reason="..."` value is itself unbreakable
        # and wider than `limit`, so its own final physical line gets an
        # auto-appended `# noqa: E501` (this IS the T-4475 fix -- the
        # over-length line the wrap produces stays E501-clean).
        src = '    # frob:waive RULE-1 reason="' + ("x" * 80) + '"\n'
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out != src
        assert len(out.splitlines()) > 1
        assert out.splitlines()[-1].endswith("  # noqa: E501")
        content_lines = [
            line[len("    # ") :].rstrip("\\") for line in out.splitlines()
        ]
        original_content = src.splitlines()[0][len("    # ") :]
        assert "".join(content_lines) == original_content + "  # noqa: E501"


# frob:ticket T-1987
# frob:ticket T-4623
class TestNoqaAlwaysPreservedT1987:
    """Asserts a `noqa`-suffixed `frob:` directive run is preserved
    byte-identical unconditionally, even when the reason text (minus the
    pragma) has a clean word-boundary wrap available -- a wrappable
    reason with a `noqa` pragma must behave identically to an
    unwrappable one."""

    # frob:ticket T-1987
    def test_wrappable_reason_keeps_its_noqa(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987.test_wrappable_reason_keeps_its_noqa  # noqa: E501
        # Space-separated words throughout -- a clean wrap would exist if
        # attempted, but the noqa pragma must still suppress the rewrap.
        words = " ".join(["word"] * 20)
        src = f'    # frob:waive RULE-1 reason="{words}"  # noqa: E501\n'
        assert len(src.splitlines()[0]) > 88
        out = canonicalize_text(src, path="a.py", limit=88)
        assert out == src

    # frob:ticket T-1987
    def test_idempotent_with_noqa_kept(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestNoqaAlwaysPreservedT1987.test_idempotent_with_noqa_kept  # noqa: E501
        words = " ".join(["word"] * 20)
        src = f'    # frob:waive RULE-1 reason="{words}"  # noqa: E501\n'
        once = canonicalize_text(src, path="a.py", limit=88)
        twice = canonicalize_text(once, path="a.py", limit=88)
        assert twice == once == src


class TestRepoWideIdempotenceT0985:
    """T-0985 acceptance bar: running the canonicalizer twice over every
    real source file this repo's `frob fmt` covers must be a no-op on the
    second pass -- `frob fmt` is idempotent-at-zero after the T-0985
    repo-wide recompaction, not just on the small hand-built fixtures
    above."""

    def test_canonicalizing_twice_over_real_repo_files_is_a_no_op(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestRepoWideIdempotenceT0985.test_canonicalizing_twice_over_real_repo_files_is_a_no_op  # noqa: E501
        root = Path(__file__).resolve().parent.parent
        limit = read_line_length(root)
        checked = 0
        for path in iter_files(root):
            if marker_for(str(path)) is None:
                continue
            try:
                with open(path, encoding="utf-8", newline="") as fh:
                    original = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            once = canonicalize_text(original, path=str(path), limit=limit)
            twice = canonicalize_text(once, path=str(path), limit=limit)
            assert twice == once, f"{path} is not idempotent under a second fmt pass"
            checked += 1
        # Sanity: this must actually exercise a non-trivial slice of the
        # repo's own source, not silently iterate zero files.
        assert checked > 100


# frob:ticket T-0991
class TestConventionUnitBinding:
    """T-0991 regression: T-0988's round-trip verification protocol found
    that wrapping a `frob:tests` directive whose target is followed by a
    trailing attribute (`kind="unit"`) could split the line right after
    the target while dropping the word-boundary space before the
    continuation -- rejoining via the REAL directive parser's comment
    extraction (which fully `.strip()`s each physical line, unlike this
    test file's own lenient `_fold_lines` helper) then silently glued
    target+attribute back together with no separator. Distinct from
    T-0987's misparse-as-new-directive class: this is silent content
    corruption INSIDE a correctly-recognized directive."""

    def test_target_plus_kind_attribute_splitting_after_target_round_trips(
        self,
    ) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestConventionUnitBinding.test_target_plus_kind_attribute_splitting_after_target_round_trips  # noqa: E501
        # limit=71 is the exact width (prefix="# " -> room=69, budget=68)
        # at which the boundary space between this target and `kind=` sits
        # precisely at index `budget` -- outside `rfind`'s exclusive search
        # range -- reproducing T-0991's exact failing shape.
        target = "tests/test_gates_fmt_directives.py::TestConventionUnitBinding.test_x"
        content_text = f'frob:tests {target} kind="unit"'
        limit = 71
        src = f"# {content_text}\n"
        out = canonicalize_text(src, path="a.py", limit=limit)
        assert out != src
        for line in out.splitlines():
            assert len(line) <= limit, f"{line!r} exceeds limit={limit}"
        physical = [line for line in out.splitlines() if line.startswith("#")]
        assert _fold_lines_real_extractor(physical, "#") == content_text

    @given(
        st.integers(min_value=5, max_value=90),
        st.integers(min_value=0, max_value=2),
        st.integers(min_value=40, max_value=120),
        st.sampled_from(["#", "//"]),
    )
    def test_logical_text_is_identical_across_widths_and_attribute_counts(
        self, target_len: int, n_attrs: int, limit: int, marker: str
    ) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestConventionUnitBinding.test_logical_text_is_identical_across_widths_and_attribute_counts  # noqa: E501
        # Property: for any target length, 0/1/2 trailing attributes, wrap
        # width 40..120, and either supported line-comment marker, wrapping
        # via `canonicalize_text` and folding the result back through the
        # REAL parser's stricter per-line strip must reproduce the exact
        # original logical directive text -- no dropped, merged, or
        # inserted characters. `target` is itself one unbreakable token
        # (no internal space), so when it is wider than the wrap budget
        # the physical line carrying it legitimately runs over `limit`
        # (T-4179: a wrapper must never split a token to force it under
        # width) -- round-trip fidelity, not per-line width, is the
        # property this test guards. T-4475: for marker == "#" (Python),
        # that same over-limit line ALSO carries an auto-appended
        # `# noqa: E501`, so the folded text is `content_text` with that
        # suffix in this case, never for marker == "//" (no E501 concept
        # there).
        target = "x" * target_len
        attrs = "".join(f' kind="unit{i}"' for i in range(n_attrs))
        content_text = f"frob:tests {target}{attrs}"
        suffix = ".py" if marker == "#" else ".rs"
        src = f"{marker} {content_text}\n"
        out = canonicalize_text(src, path=f"a{suffix}", limit=limit)
        physical = [
            line for line in out.splitlines() if line.lstrip().startswith(marker)
        ]
        folded = _fold_lines_real_extractor(physical, marker)
        assert folded in (content_text, content_text + "  # noqa: E501")


# frob:ticket T-4179
class TestNodeIdNeverSplitT4179:
    """T-4179 (consumer report F-380): the Tier-A directive re-wrapper
    split a pytest node id across the wrap -- the fragment
    `...resolves_static_impor` followed by `t kind="unit"` on the next
    physical line, so the `frob:tests` directive no longer resolved the
    test it named while still reading, to a human, as a binding. The
    MUST-FIRE fixture: a directive value wider than the wrap width is
    left unwrapped (over-`limit`) rather than split, and the emitted node
    id is byte-identical to the source, never fragmented at a `\\`
    continuation."""

    def test_pytest_node_id_directive_value_is_never_split(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestNodeIdNeverSplitT4179.test_pytest_node_id_directive_value_is_never_split  # noqa: E501
        # The exact reported shape: a `frob:tests` directive whose target
        # is a long dotted node id, immediately followed by a `kind=`
        # attribute -- the boundary the original incident split on.
        node_id = (
            "tests/unit/test_symbol_resolution.py::"
            "TestStaticImportResolver.test_resolves_static_import"
        )
        content_text = f'frob:tests {node_id} kind="unit"'
        src = f"# {content_text}\n"
        limit = 60  # narrower than `node_id` alone -- forces the wrap.
        assert len(node_id) > limit
        out = canonicalize_text(src, path="a.py", limit=limit)
        assert out != src
        # The node id must appear byte-identical, on ONE physical line --
        # never fragmented across a "\\" continuation mid-token.
        assert any(node_id in line for line in out.splitlines())
        for line in out.splitlines():
            fragment = line.strip().removeprefix("#").strip().removesuffix("\\")
            assert not (
                fragment and node_id.startswith(fragment) and fragment != node_id
            ), f"node id fragment split onto its own line: {line!r}"
        physical = [line for line in out.splitlines() if line.lstrip().startswith("#")]
        # T-4477: the node id's own trailing `kind="unit"` attribute now
        # joins it on the SAME final physical line (never split off onto
        # a middle line with no noqa of its own -- T-4474's own
        # incident), so the folded text carries the auto-appended noqa
        # suffix, same shape as TestUnbreakableTokenGetsNoqaE501T4475.
        assert (
            _fold_lines_real_extractor(physical, "#") == content_text + "  # noqa: E501"
        )


# frob:ticket T-4475
class TestUnbreakableTokenGetsNoqaE501T4475:
    """T-4475 regression: T-4179's own fix (never split an unbreakable
    directive token) left the over-`limit` physical line it produces with
    no E501 suppression, so `frob ticket land`'s pre-land `ruff check`
    reported it as a NEW violation and refused (T-4473, twice, on
    `scripts/artifact_smoke.py:52`) -- the worktree file was E501-clean
    before land's own canonicalization pass rewrote it. Fix: that final
    physical line now carries an auto-appended `# noqa: E501` (marker ==
    "#", i.e. Python -- the only `#`-comment language in `_MARKERS`, and
    E501 is a ruff/Python-specific rule)."""

    #: A 109-char pytest node id -- the same length class as T-4473's own
    #: incident (`tests/unit/test_artifact_smoke_script.py::TestCheck
    #: BaseInstall.test_failing_doctor_raises_smoke_check_error`, 107
    #: chars -- this fixture's own module/class/method names are chosen
    #: to land on exactly 109).
    _NODE_ID = (
        "tests/unit/test_artifact_smoke_script.py::"
        "TestCheckBaseInstallation.test_failing_doctor_raises_smoke_check_er"
    )

    def test_long_node_id_canonicalizes_to_one_line_ending_in_noqa(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475.test_long_node_id_canonicalizes_to_one_line_ending_in_noqa  # noqa: E501
        # `frob:tests ` itself wraps onto its own leading line (it fits
        # within budget standalone); the 109-char node id -- unbreakable,
        # wider than the budget -- lands on its OWN final physical line,
        # exactly the shape T-4473's real incident reported
        # (`scripts/artifact_smoke.py:52`, the bare node id alone at 109
        # columns). That final line, and only that one, carries the
        # auto-appended noqa.
        assert len(self._NODE_ID) == 109
        content_text = f"frob:tests {self._NODE_ID}"
        src = f"# {content_text}\n"
        out = canonicalize_text(src, path="a.py", limit=88)
        lines = out.splitlines()
        assert len(lines) == 2, f"expected two physical lines, got {lines!r}"
        assert lines[0] == "# frob:tests \\"
        assert lines[1] == f"# {self._NODE_ID}  # noqa: E501"

    def test_idempotent_on_a_second_canonicalize_pass(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475.test_idempotent_on_a_second_canonicalize_pass  # noqa: E501
        src = f"# frob:tests {self._NODE_ID}\n"
        once = canonicalize_text(src, path="a.py", limit=88)
        twice = canonicalize_text(once, path="a.py", limit=88)
        assert twice == once

    def test_directive_still_parses_to_the_same_node_id(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475.test_directive_still_parses_to_the_same_node_id  # noqa: E501
        content_text = f"frob:tests {self._NODE_ID}"
        src = f"# {content_text}\n"
        out = canonicalize_text(src, path="a.py", limit=88)
        physical = [line for line in out.splitlines() if line.lstrip().startswith("#")]
        folded = _fold_lines_real_extractor(physical, "#")
        assert folded == content_text + "  # noqa: E501"
        # The node id itself -- the part `frob:tests` binds to -- is
        # extracted the same way whether or not a trailing noqa pragma is
        # present: split on whitespace, second token.
        assert folded.split()[1] == self._NODE_ID

    def test_ruff_check_e501_is_clean_on_the_result(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenGetsNoqaE501T4475.test_ruff_check_e501_is_clean_on_the_result  # noqa: E501
        import shutil
        import subprocess

        if shutil.which("ruff") is None:
            pytest.skip("ruff binary not available")

        src = f"def f():\n    # frob:tests {self._NODE_ID}\n    pass\n"
        out = canonicalize_text(src, path="a.py", limit=88)
        target = tmp_path / "a.py"
        target.write_text(out)
        result = subprocess.run(
            ["ruff", "check", "--select", "E501", "--no-cache", str(target)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ruff check --select E501 found a violation on the "
            f"canonicalized output:\nstdout={result.stdout}\nstderr={result.stderr}"
        )


# frob:ticket T-4477
# frob:ticket T-4623
class TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477:
    """Asserts that when an unsplittable token in a directive run is
    immediately followed by a trailing `kind=`/`reason=` attribute, the
    entire remainder (attributes included) joins that token on one final
    physical line carrying a noqa, instead of leaving the token on an
    un-suppressed middle line."""

    #: The exact T-4474 incident shape: a 135-char node id (longer than
    #: any reasonable wrap budget on its own) immediately followed by a
    #: `kind="integration"` attribute.
    _NODE_ID = (
        "tests/ticket_land_suite/test_land_core.py::"
        "TestLandChainedCdRootResolution."
        "test_root_equal_to_a_real_linked_worktree_resolves_and_lands"
    )

    def test_target_plus_trailing_kind_joins_one_final_noqa_line(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477.test_target_plus_trailing_kind_joins_one_final_noqa_line  # noqa: E501
        assert len(self._NODE_ID) == 135
        content_text = f'frob:tests {self._NODE_ID} kind="integration"'
        src = f"# {content_text}\n"
        out = canonicalize_text(src, path="a.py", limit=88)
        lines = out.splitlines()
        # "frob:tests" wraps onto its own leading line; the node id and
        # its trailing kind= attribute join on ONE final line, never a
        # middle line of their own.
        assert len(lines) == 2, f"expected two physical lines, got {lines!r}"
        assert lines[0] == "# frob:tests \\"
        assert lines[1] == f'# {self._NODE_ID} kind="integration"  # noqa: E501'
        # No physical line other than the final one is over the limit --
        # the exact T-4474 defect (a middle line over budget, unmarked).
        for line in lines[:-1]:
            assert len(line) <= 88, f"non-final line over limit: {line!r}"

    def test_directive_still_parses_to_the_same_node_id_and_kind(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477.test_directive_still_parses_to_the_same_node_id_and_kind  # noqa: E501
        # `_parse_line` takes one already-FOLDED logical line (the same
        # shape `fold_comment_runs` produces from the physical lines
        # `canonicalize_text` emits) -- the real parser's own per-directive
        # entry point, one layer below the file-level `parse_directives`.
        from frob.graph.dsl import _parse_line

        content_text = f'frob:tests {self._NODE_ID} kind="integration"'
        src = f"# {content_text}\n"
        out = canonicalize_text(src, path="a.py", limit=88)
        physical = [line for line in out.splitlines() if line.lstrip().startswith("#")]
        folded = _fold_lines_real_extractor(physical, "#")
        edge = _parse_line(folded, path="a.py", lineno=1, src="")
        assert edge is not None and not hasattr(edge, "reason"), (
            f"expected a parsed Edge, got {edge!r}"
        )
        assert edge.target == self._NODE_ID
        assert edge.attrs.get("kind") == "integration"

    def test_idempotent_on_a_second_canonicalize_pass(self) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477.test_idempotent_on_a_second_canonicalize_pass  # noqa: E501
        src = f'# frob:tests {self._NODE_ID} kind="integration"\n'
        once = canonicalize_text(src, path="a.py", limit=88)
        twice = canonicalize_text(once, path="a.py", limit=88)
        assert twice == once

    def test_ruff_check_e501_is_clean_on_every_line(self, tmp_path: Path) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestUnbreakableTokenWithTrailingAttrGetsNoqaT4477.test_ruff_check_e501_is_clean_on_every_line  # noqa: E501
        import shutil
        import subprocess

        if shutil.which("ruff") is None:
            pytest.skip("ruff binary not available")

        src = (
            f'def f():\n    # frob:tests {self._NODE_ID} kind="integration"\n    pass\n'
        )
        out = canonicalize_text(src, path="a.py", limit=88)
        target = tmp_path / "a.py"
        target.write_text(out)
        result = subprocess.run(
            ["ruff", "check", "--select", "E501", "--no-cache", str(target)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ruff check --select E501 found a violation on the "
            f"canonicalized output:\nstdout={result.stdout}\nstderr={result.stderr}"
        )


class TestQuotedTargetNeverSplitByWrap:
    """T-4712: `_wrap_cut_point`'s narrowing -- a cut may never land inside
    a QUOTED target (a vitest-style describe title), even when that
    target contains internal spaces the pre-T-4712 word-boundary scan
    would happily cut at."""

    def test_pre_change_word_boundary_cut_would_have_split_the_quoted_target(
        self,
    ) -> None:
        # frob:tests \
        # tests/test_gates_fmt_directives.py::TestQuotedTargetNeverSplitByWrap.test_pre_change_word_boundary_cut_would_have_split_the_quoted_target  # noqa: E501
        # The CONTROL: the raw word-boundary rule this leaf narrows
        # (`remaining.rfind(" ", 0, budget)` with no protected-span
        # check at all) DOES land inside the quoted target here -- if
        # this assertion ever stopped holding, the "clean" assertion
        # below would no longer be exercising anything.
        remaining = (
            'frob:tests "src/x.test.ts a fairly long describe title with '
            'several words in it"'
        )
        budget = 30
        naive_cut = remaining.rfind(" ", 0, budget)
        assert naive_cut > 0
        assert remaining[0] == "f"  # sanity: this is the whole line
        # The naive cut position is inside the quoted target span
        # (opens right after `frob:tests `, well before column 30).
        open_quote = remaining.index('"')
        close_quote = remaining.rindex('"')
        assert open_quote < naive_cut < close_quote

    def test_quoted_target_is_never_split_across_physical_lines(self) -> None:
        src = (
            "def foo() -> None:\n"
            '    # frob:tests "src/x.test.ts a fairly long describe title '
            'with several words in it"\n'
            "    pass\n"
        )
        out = canonicalize_text(src, path="a.py", limit=40)
        # The quote count across the whole output is unchanged (2 --
        # nothing duplicated or dropped), and exactly ONE physical line
        # carries BOTH quotes -- the title is never split mid-string.
        assert out.count('"') == 2
        quote_lines = [line for line in out.splitlines() if line.count('"') == 2]
        assert len(quote_lines) == 1
        assert (
            '"src/x.test.ts a fairly long describe title with several words in it"'
        ) in out


class TestUnbreakableSingleNodeIdStillUnsplittable:
    """T-4712 positive control: a `frob:tests` whose single node id alone
    exceeds the line length keeps the pre-existing unsplittable-remainder
    path -- exactly one final line carrying the noqa suffix, unaffected
    by this leaf's quoted-target narrowing (there is no quote at all
    here)."""

    def test_single_long_node_id_produces_one_noqa_suffixed_line(self) -> None:
        node_id = "tests/" + ("x" * 90) + ".py::TestClass.test_method"
        src = f"def f():\n    # frob:tests {node_id}\n    pass\n"
        out = canonicalize_text(src, path="a.py", limit=88)
        directive_lines = [line for line in out.splitlines() if node_id in line]
        assert len(directive_lines) == 1
        assert directive_lines[0].rstrip().endswith("# noqa: E501")


class TestCanonicalizeTextIdempotentTwice:
    """T-4712 positive control: `format_paths` (via `canonicalize_text`)
    reports zero further changes on a second run -- narrowing the cut
    point must stay a canonicalizer, not a one-way wrapper."""

    def test_second_format_paths_run_reports_zero_changes(self, tmp_path) -> None:  # noqa: ANN001
        target = tmp_path / "a.py"
        target.write_text(
            "def f():\n"
            '    # frob:tests "src/x.test.ts a fairly long describe title '
            'with several words in it"\n'
            "    pass\n"
        )
        first = format_paths(tmp_path, check_only=False, limit=40)
        assert [c.path for c in first.changes] == ["a.py"]
        second = format_paths(tmp_path, check_only=False, limit=40)
        assert second.changes == ()
