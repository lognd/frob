"""Tests for `frob.lang`'s CSS/SCSS wiring (T-5303, docs/modules/lang.md).

A dedicated file (not `tests/test_lang.py`) deliberately, to keep T-5303's
touched set disjoint from T-5300's concurrent html/javascript/vue wiring
in the same shared dispatch tables -- see this ticket's Done report.
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import SymbolKind, parse_file, raw_tree, supported_languages

_FIXTURES = Path(__file__).parent / "fixtures" / "lang"


def _symbol(pf, qualname: str):
    """First symbol on `pf` whose qualname matches (test helper)."""
    return next(s for s in pf.symbols if s.qualname == qualname)


# frob:ticket T-5303
class TestCss:
    """`.css` wiring (`frob.lang._walk_css.walk_css`)."""

    def test_css_is_a_supported_language(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_languages
        assert "css" in supported_languages()

    def test_parse_css_sample(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file
        pf = parse_file(_FIXTURES / "sample.css").danger_ok
        assert pf.language == "css"
        assert pf.symbols

    def test_positive_control_raw_tree_is_non_empty(self) -> None:
        # frob:tests src/frob/lang/__init__.py::raw_tree
        tree, _source, language_label = raw_tree(_FIXTURES / "sample.css").danger_ok
        assert language_label == "css"
        assert tree.root_node.children

    def test_top_level_rule_set_is_a_class_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_css.py::walk_css
        pf = parse_file(_FIXTURES / "sample.css").danger_ok
        button = _symbol(pf, ".button, .button--primary")
        assert button.kind == SymbolKind.CLASS
        assert button.public is True

    def test_nested_rule_inside_media_is_not_a_top_level_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_css.py::_walk_css_family
        pf = parse_file(_FIXTURES / "sample.css").danger_ok
        names = {s.qualname for s in pf.symbols}
        assert ".nested-rule" not in names


# frob:ticket T-5303
class TestScss:
    """`.scss` wiring (`frob.lang._walk_css.walk_scss`)."""

    def test_scss_is_a_supported_language(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_languages
        assert "scss" in supported_languages()

    def test_parse_scss_sample(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file
        pf = parse_file(_FIXTURES / "sample.scss").danger_ok
        assert pf.language == "scss"
        assert pf.symbols

    def test_positive_control_raw_tree_is_non_empty_nested_selector(self) -> None:
        # frob:tests src/frob/lang/__init__.py::raw_tree
        # Positive control: the nested `&:hover { ... }` selector inside
        # `.card` parses to a non-empty raw tree (this ticket's own
        # required control -- "a nested selector parses to a non-empty
        # raw tree").
        tree, _source, language_label = raw_tree(_FIXTURES / "sample.scss").danger_ok
        assert language_label == "scss"
        assert tree.root_node.children

    def test_dollar_variable_is_a_const_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_css.py::_scss_variable_symbol
        pf = parse_file(_FIXTURES / "sample.scss").danger_ok
        brand = _symbol(pf, "$brand-color")
        assert brand.kind == SymbolKind.CONST
        assert brand.public is True

    def test_top_level_rule_set_is_a_class_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_css.py::walk_scss
        pf = parse_file(_FIXTURES / "sample.scss").danger_ok
        card = _symbol(pf, ".card")
        assert card.kind == SymbolKind.CLASS
        assert card.public is True

    def test_line_comment_is_recognized(self) -> None:
        # frob:tests src/frob/lang/_walk_css.py::SCSS_COMMENT_TYPES
        pf = parse_file(_FIXTURES / "sample.scss").danger_ok
        assert any("frob:tests" in c.text for c in pf.comments)
