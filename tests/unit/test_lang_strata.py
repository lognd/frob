"""Tests for the `.strata` grammar in `frob.lang` (docs/modules/lang.md#strata, T-0077).

Exercises `frob.lang.parse_file` against a real litmus design file
(design/litmus/chirp.strata) plus small hand-built fixtures for the error
path and the tree-sitter-escape-hatch functions that stay unsupported for
`.strata`.
"""


from __future__ import annotations

import sys
from pathlib import Path

import pytest

from frob.lang import (
    LangError,
    SymbolKind,
    extract_imports,
    parse_file,
    raw_tree,
    supported_extensions,
    supported_languages,
    symbol_tree,
)
from frob.lang._walk_strata import (
    NATIVE_UNAVAILABLE_MESSAGE,
    _declared_items,
    _locate_declared_items,
    walk_strata,
)

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
        # frob:tests src/frob/lang/_common.py::_find_following_symbol kind="unit"
        pf = parse_file(_LITMUS).danger_ok
        assert any(c.following == "chirp.tweets" for c in pf.comments)

    def test_comment_inside_a_block_binds_as_enclosing(self, tmp_path: Path) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        # frob:tests src/frob/lang/_common.py::_find_enclosing_symbol kind="unit"
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


class TestStrataNativeParserUnavailable:
    """T-0133: standalone tool installs have no `strata_core` extension.

    Simulates that install shape by monkeypatching the module-level
    `strata_core` binding to `None` -- the same state a bare `uv tool
    install frob` leaves it in -- and checks every consumer degrades to a
    typed `Result.Err` instead of crashing or logging like a real parse
    failure.
    """

    @pytest.fixture(autouse=True)
    def _no_native_parser(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # `frob.lang.__init__` rebinds the package attribute
        # `frob.lang._walk_strata` to the `walk_strata` function (its own
        # `from ... import walk_strata as _walk_strata`), shadowing the real
        # submodule object -- go through `sys.modules` for the actual
        # submodule so this monkeypatch lands on the binding `walk_strata`
        # itself reads at call time.
        walk_strata_mod = sys.modules["frob.lang._walk_strata"]
        monkeypatch.setattr(walk_strata_mod, "strata_core", None)

    def test_walk_strata_returns_err(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        result = walk_strata("module m\nnode n : trusted {\n}\n")
        assert result.is_err
        assert result.danger_err == NATIVE_UNAVAILABLE_MESSAGE

    def test_parse_file_returns_native_parser_unavailable(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file kind="unit"
        result = parse_file(_LITMUS)
        assert result.is_err
        assert result.danger_err == LangError.NativeParserUnavailable

    def test_strata_extension_still_advertised(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_extensions kind="unit"
        # (a) decision: .strata stays listed even with no native parser --
        # the graph should still SEE the files exist, just fail to parse
        # each one with a typed Err rather than being invisible to xref/
        # coverage/gates entirely.
        assert ".strata" in supported_extensions()

    def test_graph_build_skips_quietly(self, tmp_path: Path) -> None:
        # frob:tests src/frob/graph/__init__.py::build_graph kind="unit"
        from frob.graph import build_graph

        (tmp_path / "a.strata").write_text("module m\nnode n : trusted {\n}\n")
        result = build_graph(tmp_path, tmp_path / ".frob-cache.sqlite")
        assert result.is_ok, "a missing native parser must not crash build_graph"

    def test_outline_file_returns_err_not_crash(self) -> None:
        # frob:tests src/frob/outline/__init__.py::outline_file kind="unit"
        from frob.outline import outline_file

        result = outline_file(_LITMUS)
        assert result.is_err

    def test_map_file_node_degrades_without_raising(self, tmp_path: Path) -> None:
        # frob:tests src/frob/map/__init__.py::_file_node kind="unit"
        from frob.map import _file_node

        path = tmp_path / "a.strata"
        path.write_text("module m\nnode n : trusted {\n}\n")
        node = _file_node(tmp_path, path)
        assert node.lines > 0

    def test_xref_search_does_not_raise(self, tmp_path: Path) -> None:
        # frob:tests src/frob/xref/__init__.py::_parsed_definition kind="unit"
        from frob.xref import _parsed_definition

        path = tmp_path / "a.strata"
        path.write_text("module m\nnode n : trusted {\n}\n")
        assert _parsed_definition(path, "n", "a.strata") is None


# frob:ticket T-2187
class TestGrammarAuthoritativeSymbols:
    """T-2187: `walk_strata`'s symbols come from strata-core's structured
    parse (`_declared_items`), not from a line-regex's own guess -- the
    header-regex line scan only LOCATES a span for a construct the grammar
    already said exists, and a construct it cannot locate fails the whole
    walk closed. Every case here reproduces a REAL disagreement shape
    measured in this repo's own `.strata` corpus (`frob verify explain`:
    16 header-regex-count != strata-core-declared-count warnings), not a
    synthetic worst case."""

    def test_quoted_string_claim_id_is_extracted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        # T-2187's own root cause, reproduced minimally: `assume "..." ...`
        # -- a quoted-string claim id -- is real syntax (design/frob.strata
        # has 32 of these) that the pre-T-2187 `_HEADER_RE`'s
        # `[A-Za-z_][A-Za-z0-9_]*` identifier group could never match at
        # all (a `"` is not an identifier character), so this symbol was
        # silently absent from `pf.symbols` on main with only a WARNING
        # log line, never surfaced to the caller. This test MUST fail
        # against current main (the symbol is simply missing there).
        src = (
            "module m\n"
            'node registry : trusted { clearance Internal; }\n'
            'assume "weakness:CWE-78:claude_hooks" noflow registry -> claude_hooks '
            'owner logan review "2026-10-15"\n'
        )
        path = tmp_path / "quoted_claim.strata"
        path.write_text(src)
        pf = parse_file(path).danger_ok
        names = {s.qualname for s in pf.symbols}
        assert "m.weakness:CWE-78:claude_hooks" in names, (
            "a quoted-string claim id must be extracted as a real symbol, "
            f"got: {sorted(names)}"
        )
        claim_sym = _symbol(pf, "m.weakness:CWE-78:claude_hooks")
        assert claim_sym.kind == SymbolKind.CONST

    def test_resource_declaration_is_extracted(self, tmp_path: Path) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        # `resource` was entirely absent from the pre-T-2187 keyword
        # vocabulary (`_HEADER_RE`/`_KEYWORD_KIND` both lacked it) despite
        # being real syntax used 3 times in this repo's own corpus
        # (design/frob.strata, tests/unit/strata/litmus/contention_*
        # _arbitered.strata) -- every `resource` declaration undercounted
        # the regex-derived symbol count by exactly one. This test MUST
        # fail against current main (no `resource` symbol is ever
        # produced there at all).
        src = 'module m\nresource shared_lock {\n    lock "the-lock";\n}\n'
        path = tmp_path / "resource_decl.strata"
        path.write_text(src)
        pf = parse_file(path).danger_ok
        names = {s.qualname for s in pf.symbols}
        assert "m.shared_lock" in names, f"resource symbol missing, got: {sorted(names)}"
        resource_sym = _symbol(pf, "m.shared_lock")
        assert resource_sym.kind == SymbolKind.CLASS
        start, end = resource_sym.span
        assert end > start

    def test_locator_fails_closed_on_a_construct_it_cannot_find(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::_locate_declared_items kind="unit"
        # Direct unit coverage of the fail-closed contract itself (T-2187
        # acceptance criterion 2): a declared item with no corresponding
        # header line in `lines` must come back in `unmatched`, never be
        # silently dropped from the returned symbol count.
        lines = ["module m", "node n : trusted {", "}"]
        declared = [("module", "m"), ("node", "n"), ("node", "phantom")]
        symbols, unmatched = _locate_declared_items(lines, declared)
        assert unmatched == [("node", "phantom")]
        assert {s.qualname for s in symbols} == {"m", "m.n"}

    def test_walk_strata_returns_err_not_a_log_line_on_disagreement(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::walk_strata kind="unit"
        # The ticket's central prohibition: a grammar/locator disagreement
        # must refuse the whole walk (`Err`), never log a warning and
        # return the (now-known-incomplete) symbol set anyway -- the
        # pre-T-2187 behavior this replaces. Forces disagreement by
        # monkeypatching `_declared_items` to report one extra phantom
        # construct no source line can ever satisfy. Goes through
        # `sys.modules` for the real submodule, not the `frob.lang`
        # package-level rebinding (`from ... import walk_strata as
        # _walk_strata` shadows the submodule name there) -- same
        # necessity as `TestStrataNativeParserUnavailable._no_native_
        # parser` above.
        walk_strata_mod = sys.modules["frob.lang._walk_strata"]
        original_declared_items = walk_strata_mod._declared_items
        monkeypatch.setattr(
            walk_strata_mod,
            "_declared_items",
            lambda parsed_ok: [
                *original_declared_items(parsed_ok),
                ("node", "this_id_does_not_exist_in_source"),
            ],
        )
        result = walk_strata("module m\nnode n : trusted {\n}\n")
        assert result.is_err
        assert "this_id_does_not_exist_in_source" in result.danger_err
        assert "refusing" in result.danger_err

    def test_declared_items_covers_every_keyword_family(self) -> None:
        # frob:tests src/frob/lang/_walk_strata.py::_declared_items kind="unit"
        # One representative of each `Module` list field, including the
        # two families the pre-T-2187 regex mishandled (`claims` via a
        # quoted id, `resources` not recognized at all) -- guards against
        # a future `Module` field being added to strata-core's schema
        # without a matching `_FIELD_TO_KEYWORD` entry ever being noticed.
        parsed_ok = {
            "name": "m",
            "nodes": [{"id": "n1"}],
            "flows": [{"id": "f1"}],
            "boundaries": [{"id": "b1"}],
            "stores": [{"id": "s1"}],
            "caches": [{"id": "c1"}],
            "queues": [{"id": "q1"}],
            "cdns": [{"id": "cdn1"}],
            "balancers": [{"id": "bal1"}],
            "policies": [{"id": "p1"}],
            "operations": [{"id": "op1"}],
            "scenarios": [{"id": "sc1"}],
            "resources": [{"id": "r1"}],
            "refines": [{"target": "t1"}],
            "claims": [
                {"id": "assert1", "assumed": False},
                {"id": "assume1", "assumed": True},
            ],
            "secrets": [],
        }
        items = _declared_items(parsed_ok)
        assert ("module", "m") in items
        assert ("node", "n1") in items
        assert ("flow", "f1") in items
        assert ("boundary", "b1") in items
        assert ("store", "s1") in items
        assert ("cache", "c1") in items
        assert ("queue", "q1") in items
        assert ("cdn", "cdn1") in items
        assert ("balancer", "bal1") in items
        assert ("policy", "p1") in items
        assert ("operation", "op1") in items
        assert ("scenario", "sc1") in items
        assert ("resource", "r1") in items
        assert ("refine", "t1") in items
        assert ("assert", "assert1") in items
        assert ("assume", "assume1") in items
        # "secrets" has no keyword mapping in `_FIELD_TO_KEYWORD` -- not a
        # symbol-family this walker's SymbolKind vocabulary covers (no
        # header syntax it needs to locate a span for either); its
        # presence in `parsed_ok` must not raise or silently inflate
        # `items` with a bogus entry.
        assert len(items) == 16
