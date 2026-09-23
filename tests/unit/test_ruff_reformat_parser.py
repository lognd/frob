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
