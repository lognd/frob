"""Tests for `frob.lang`'s html/javascript/jsx/vue wiring (T-5300,
docs/modules/lang.md).

A dedicated file (not `tests/test_lang.py`), the same convention
`tests/test_lang_css.py` uses for T-5303 -- keeps this ticket's touched
set disjoint from any other concurrent `frob.lang` wiring ticket sharing
the same dispatch tables.
"""

from __future__ import annotations

from pathlib import Path

from frob.lang import SymbolKind, parse_file, raw_tree, supported_languages

_FIXTURES = Path(__file__).parent / "fixtures" / "lang"


def _symbol(pf, qualname: str):
    """First symbol on `pf` whose qualname matches (test helper)."""
    return next(s for s in pf.symbols if s.qualname == qualname)


# frob:ticket T-5300
class TestHtml:
    """`.html` wiring (`frob.lang._walk_html._walk_html`)."""

    def test_html_is_a_supported_language(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_languages
        assert "html" in supported_languages()

    def test_parse_html_sample(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file
        pf = parse_file(_FIXTURES / "sample.html").danger_ok
        assert pf.language == "html"
        assert pf.symbols

    def test_positive_control_raw_tree_is_non_empty(self) -> None:
        # frob:tests src/frob/lang/__init__.py::raw_tree
        tree, _source, language_label = raw_tree(_FIXTURES / "sample.html").danger_ok
        assert language_label == "html"
        assert tree.root_node.children

    def test_top_level_element_is_a_class_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_html.py::_walk_html
        pf = parse_file(_FIXTURES / "sample.html").danger_ok
        html_el = _symbol(pf, "html")
        assert html_el.kind == SymbolKind.CLASS
        assert html_el.public is True


# frob:ticket T-5300
class TestJsx:
    """`.jsx` wiring (`frob.lang._walk_javascript._walk_javascript`, same
    "javascript" grammar/walker `.js` uses -- mirrors `.tsx` reusing
    "tsx"/`_walk_typescript`)."""

    def test_jsx_is_a_supported_extension(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_extensions
        from frob.lang import supported_extensions

        assert ".jsx" in supported_extensions()

    def test_parse_jsx_sample(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file
        pf = parse_file(_FIXTURES / "sample.jsx").danger_ok
        assert pf.language == "javascript"
        assert pf.symbols

    def test_positive_control_raw_tree_is_non_empty(self) -> None:
        # frob:tests src/frob/lang/__init__.py::raw_tree
        tree, _source, language_label = raw_tree(_FIXTURES / "sample.jsx").danger_ok
        assert language_label == "javascript"
        assert tree.root_node.children
        assert not tree.root_node.has_error

    def test_exported_function_is_a_public_function_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_javascript.py::_walk_javascript
        pf = parse_file(_FIXTURES / "sample.jsx").danger_ok
        greeting = _symbol(pf, "Greeting")
        assert greeting.kind == SymbolKind.FUNCTION
        assert greeting.public is True


# frob:ticket T-5300
class TestVue:
    """`.vue` SFC-shell wiring (`frob.lang._walk_vue._walk_vue`)."""

    def test_vue_is_a_supported_language(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_languages
        assert "vue" in supported_languages()

    def test_parse_vue_sample(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file
        pf = parse_file(_FIXTURES / "sample.vue").danger_ok
        assert pf.language == "vue"
        assert pf.symbols

    def test_positive_control_raw_tree_is_non_empty(self) -> None:
        # frob:tests src/frob/lang/__init__.py::raw_tree
        tree, _source, language_label = raw_tree(_FIXTURES / "sample.vue").danger_ok
        assert language_label == "vue"
        assert tree.root_node.children

    def test_template_block_is_a_class_symbol(self) -> None:
        # frob:tests src/frob/lang/_walk_vue.py::_walk_vue
        pf = parse_file(_FIXTURES / "sample.vue").danger_ok
        template = _symbol(pf, "template")
        assert template.kind == SymbolKind.CLASS
        assert template.public is True

    def test_sfc_shell_has_exactly_three_blocks(self) -> None:
        # frob:tests src/frob/lang/_walk_vue.py::_walk_vue
        pf = parse_file(_FIXTURES / "sample.vue").danger_ok
        names = {s.qualname for s in pf.symbols}
        assert names == {"template", "script", "style"}
