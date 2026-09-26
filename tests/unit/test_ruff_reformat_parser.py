"""T-5393: `frob.process.parsers.ruff.parse_ruff_would_reformat_paths` --
the single shared parser for `ruff format --check`'s "Would reformat"
lines, replacing the two partial (colon-blind) copies that used to live
in `frob.gates._land_format` and `frob.check._python`. Positive control:
both the colon (ruff >=0.15.16) and colon-less (older ruff) line shapes
must resolve to the same real path string."""

from __future__ import annotations

from frob.process.parsers.ruff import parse_ruff_would_reformat_paths


# frob:tests src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_paths
def test_colon_form_returns_real_path() -> None:
    """Newer ruff (0.15.16+): `Would reformat: <path>` -- the colon must
    not become part of the returned path (the T-5393 bug: a leftover
    `Would reformat: <path>` string used verbatim as a filename)."""
    out = parse_ruff_would_reformat_paths("Would reformat: src/feature.py\n")
    assert out == ("src/feature.py",)


# frob:tests src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_paths
def test_colonless_form_returns_real_path() -> None:
    """Older ruff: `Would reformat <path>` (no colon) -- must keep
    parsing exactly as before this change."""
    out = parse_ruff_would_reformat_paths("Would reformat src/feature.py\n")
    assert out == ("src/feature.py",)


# frob:tests src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_paths
def test_multiple_lines_both_shapes_sorted() -> None:
    """Mixed colon and colon-less lines across a multi-file `ruff format
    --check` run all resolve, sorted for determinism."""
    stdout = "Would reformat: b/two.py\nWould reformat a/one.py\n"
    out = parse_ruff_would_reformat_paths(stdout)
    assert out == ("a/one.py", "b/two.py")


# frob:tests src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_paths
def test_non_matching_line_contributes_nothing() -> None:
    """A line outside the "Would reformat" grammar (e.g. a summary line)
    is ignored, never misparsed into a bogus path."""
    stdout = "Would reformat: a/one.py\n1 file would be reformatted\n"
    out = parse_ruff_would_reformat_paths(stdout)
    assert out == ("a/one.py",)


# frob:tests src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_paths
def test_empty_input_returns_empty_tuple() -> None:
    """No "Would reformat" output at all -- empty tuple, not an error."""
    assert parse_ruff_would_reformat_paths("") == ()


# frob:ticket T-draft-cbdee0d3
class TestRuff0165UnformattedArrowGrammar:
    """T-draft-cbdee0d3: ruff 0.16.5 replaced "Would reformat[:] <path>"
    with an `unformatted:` diagnostic header followed by a `--> <path>:
    <line>:<col>` locator line and a diff block. Positive control: this
    exact shape yields the real path; the companion control confirms a
    whole-run `ToolResult` built from that output (the way `_ruff_format_
    result` builds one) carries real diagnostics on a nonzero exit,
    never the empty-diagnostics shape the T-2521 completeness check
    correctly reads as unmeasurable."""

    # 0.16.5's real shape, one file, trimmed to the header/locator/diff
    # lines that matter to this parser plus the trailing summary line.
    _SAMPLE_STDOUT = (
        "unformatted: File would be reformatted\n"
        "  --> tests/unit/test_gallery_manifest.py:23:16\n"
        "   |\n"
        "23 | def foo( x,y ):\n"
        "   |                ^\n"
        "24 |     return x+y\n"
        "   |\n"
        "1 file would be reformatted, 154 files already formatted\n"
    )

    # frob:tests src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_paths
    def test_arrow_line_yields_the_real_path(self) -> None:
        """The `--> <path>:<line>:<col>` locator line resolves to the
        bare path, `<line>:<col>` discarded -- never the whole diagnostic
        block treated as one unparseable blob."""
        out = parse_ruff_would_reformat_paths(self._SAMPLE_STDOUT)
        assert out == ("tests/unit/test_gallery_manifest.py",)

    # frob:tests src/frob/check/_python.py::_ruff_format_result
    def test_whole_run_tool_result_carries_diagnostics_on_nonzero_exit(
        self,
    ) -> None:
        """The `ToolResult` shape `_ruff_format_result` builds from this
        output (`exit_code=1`, one `Diagnostic` per real path) must carry
        N real diagnostics, not an empty list -- the exact shape the
        T-2521 completeness check (`_verify.py::_incomplete_tool_
        results`) needs to read this as MEASURED format drift instead of
        a crashed/silent tool stage."""
        from frob.check._python import _reformat_diagnostics
        from frob.process.parsers.common import ToolResult

        paths = parse_ruff_would_reformat_paths(self._SAMPLE_STDOUT)
        diagnostics = _reformat_diagnostics(paths)
        result = ToolResult(
            tool="ruff-format",
            exit_code=1,
            diagnostics=diagnostics,
            summary=f"{len(paths)} file(s) would be reformatted",
        )

        assert result.exit_code == 1
        assert len(result.diagnostics) == 1
        assert result.diagnostics[0].file == "tests/unit/test_gallery_manifest.py"
        assert result.diagnostics[0].severity == "warning"

    # frob:tests src/frob/process/parsers/ruff.py::parse_ruff_would_reformat_paths
    def test_multiple_files_both_arrow_and_colon_forms_mixed(self) -> None:
        """A mixed-grammar run (unlikely in practice -- one ruff binary
        emits one grammar per invocation -- but the parser must not care
        which) resolves every real path, sorted and de-duplicated."""
        stdout = (
            "unformatted: File would be reformatted\n"
            "  --> b/two.py:1:1\n"
            "Would reformat: a/one.py\n"
        )
        out = parse_ruff_would_reformat_paths(stdout)
        assert out == ("a/one.py", "b/two.py")
