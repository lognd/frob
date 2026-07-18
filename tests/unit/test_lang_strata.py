"""Tests for the `.strata` grammar in `frob.lang` (docs/modules/lang.md#strata, T-0077).

Exercises `frob.lang.parse_file` against a real litmus design file
(design/litmus/chirp.strata) plus small hand-built fixtures for the error
path and the tree-sitter-escape-hatch functions that stay unsupported for
`.strata`.
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import (
    LangError,
    SymbolKind,
    extract_imports,
    parse_file,
    raw_tree,
    supported_languages,
    symbol_tree,
)
from frob.lang._walk_strata import walk_strata

_LITMUS = Path(__file__).resolve().parents[2] / "design" / "litmus" / "chirp.strata"


def _symbol(pf, qualname: str):
    return next(s for s in pf.symbols if s.qualname == qualname)


class TestParseStrata:
    def test_strata_is_a_supported_language(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_languages kind="unit"
        assert "strata" in supported_languages()

    def test_symbols_kinds_and_module_qualnames(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file kind="unit"
        pf = parse_file(_LITMUS).danger_ok
        assert pf.language == "strata"
        names = {s.qualname for s in pf.symbols}
        assert {
            "chirp",
            "chirp.author",
            "chirp.tweets_hot",
            "chirp.tweets",
            "chirp.timeline",
            "chirp.f_ingest",
            "chirp.b_ingest",
            "chirp.c_hot_shard_utilization",
        } <= names

        module_sym = _symbol(pf, "chirp")
        assert module_sym.kind == SymbolKind.CLASS
        node_sym = _symbol(pf, "chirp.tweets_hot")
        assert node_sym.kind == SymbolKind.CLASS
        flow_sym = _symbol(pf, "chirp.f_ingest")
        assert flow_sym.kind == SymbolKind.FUNCTION
        boundary_sym = _symbol(pf, "chirp.b_ingest")
        assert boundary_sym.kind == SymbolKind.FUNCTION
        claim_sym = _symbol(pf, "chirp.c_hot_shard_utilization")
        assert claim_sym.kind == SymbolKind.CONST

    def test_all_symbols_are_public(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file kind="unit"
        pf = parse_file(_LITMUS).danger_ok
        assert all(s.public for s in pf.symbols)

    def test_multiline_construct_span_covers_its_block(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        pf = parse_file(_LITMUS).danger_ok
        node_sym = _symbol(pf, "chirp.tweets_hot")
        start, end = node_sym.span
        assert end > start
        assert "capacity" in node_sym.body_tokens

    def test_single_line_construct_span_is_one_line(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        pf = parse_file(_LITMUS).danger_ok
        flow_sym = _symbol(pf, "chirp.f_tweet_write")
        assert flow_sym.span[0] == flow_sym.span[1]

    def test_leading_comment_becomes_doc_text(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        pf = parse_file(_LITMUS).danger_ok
        store_sym = _symbol(pf, "chirp.tweets")
        assert "source of truth" in store_sym.doc_text.lower()

    def test_comments_bind_following_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        # frob:tests src/frob/lang/_common.py::find_following_symbol kind="unit"
        pf = parse_file(_LITMUS).danger_ok
        assert any(c.following == "chirp.tweets" for c in pf.comments)

    def test_comment_inside_a_block_binds_as_enclosing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        # frob:tests src/frob/lang/_common.py::find_enclosing_symbol kind="unit"
        src = (
            "module m\n"
            "node n : trusted {\n"
            "    // inside the block\n"
            "    clearance Internal;\n"
            "}\n"
        )
        path = tmp_path / "inner.strata"
        path.write_text(src)
        pf = parse_file(path).danger_ok
        inside = [c for c in pf.comments if c.enclosing == "m.n"]
        assert inside, (
            "a comment strictly between a construct's braces must bind as enclosing"
        )

    def test_content_hash_is_stable_across_reparse(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file kind="unit"
        first = parse_file(_LITMUS).danger_ok
        second = parse_file(_LITMUS).danger_ok
        assert first.content_hash == second.content_hash

    def test_parse_failure_returns_parse_failed(self, tmp_path: Path) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file kind="unit"
        bad = tmp_path / "broken.strata"
        bad.write_text("module x\nnode !!! garbage")
        result = parse_file(bad)
        assert result.is_err
        assert result.danger_err == LangError.ParseFailed

    def test_walk_strata_err_on_bad_syntax(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        result = walk_strata("node !!! garbage")
        assert result.is_err
        assert "line" in result.danger_err


class TestStrataTreeSitterEscapeHatchesUnsupported:
    """`.strata` has no tree-sitter Tree -- the node-level escape hatches
    correctly refuse it rather than silently returning nonsense."""

    def test_raw_tree_unsupported_for_strata(self) -> None:
        # frob:tests src/frob/lang/__init__.py::raw_tree kind="unit"
        assert raw_tree(_LITMUS).danger_err == LangError.UnsupportedLanguage

    def test_extract_imports_unsupported_for_strata(self) -> None:
        # frob:tests src/frob/lang/__init__.py::extract_imports kind="unit"
        assert extract_imports(_LITMUS).danger_err == LangError.UnsupportedLanguage

    def test_symbol_tree_unsupported_for_strata(self) -> None:
        # frob:tests src/frob/lang/__init__.py::symbol_tree kind="unit"
        assert symbol_tree(_LITMUS, (1, 2)).danger_err == LangError.UnsupportedLanguage
