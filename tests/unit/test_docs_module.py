"""Unit tests for frob.docs: docstring extraction and docs-directory search."""

from __future__ import annotations

from pathlib import Path

from frob.docs import extract_docstrings, find_docs_dir, overview, search

# T-3232: shared static csharp fixture (also used by tests/test_lang.py's
# TestCSharp) -- a namespaced public class with XML `<summary>` doc
# comments on both the class and a method, plus a same-class method call,
# reused here instead of a second hand-authored csharp source.
_FIXTURES = Path(__file__).parent.parent / "fixtures" / "lang"


def test_extract_docstrings(tmp_path):
    # frob:tests src/frob/docs/__init__.py::extract_docstrings kind="unit"
    src = tmp_path / "mod.py"
    src.write_text(
        '"""Module doc."""\n\n\ndef foo():\n    """Foo does the thing."""\n    pass\n'
    )
    docs = extract_docstrings(src)
    assert any(d.symbol == "foo" and "Foo does the thing" in d.text for d in docs)


def test_find_docs_dir(tmp_path):
    # frob:tests src/frob/docs/__init__.py::find_docs_dir kind="unit"
    (tmp_path / "docs").mkdir()
    nested = tmp_path / "src" / "pkg"
    nested.mkdir(parents=True)
    found = find_docs_dir(nested)
    assert found == tmp_path / "docs"


def test_overview(tmp_path):
    # frob:tests src/frob/docs/__init__.py::overview kind="unit"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "widget.md").write_text("# widget\n\nDescribes the widget module.\n")
    src = tmp_path / "widget.py"
    src.write_text("x = 1\n")
    entries = overview(src)
    assert any("widget" in e.heading.lower() for e in entries)


def test_search(tmp_path):
    # frob:tests src/frob/docs/__init__.py::search kind="unit"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "widget.md").write_text("# widget\n\nDescribes the widget module.\n")
    matches = search("widget", docs_dir)
    assert matches
    assert any("widget" in m.heading.lower() for m in matches)


def test_extract_docstrings_non_python_file_returns_empty(tmp_path):
    """Proves `extract_docstrings` returns `[]` for a language
    `frob.lang` has no grammar for at all (`.frobnotalang`), the
    contract this test's name still names as "non-python" while C# is a
    supported language covered separately, see
    `test_extract_docstrings_csharp_class_and_method` (T-3232, T-1286)."""
    # frob:tests src/frob/docs/__init__.py::extract_docstrings kind="unit"
    src = tmp_path / "mod.frobnotalang"
    src.write_text("/// A doc comment for a language that does not exist.\n")
    assert extract_docstrings(src) == []


def test_extract_docstrings_csharp_class_and_method(tmp_path):
    # frob:tests src/frob/docs/__init__.py::extract_docstrings kind="unit"
    # T-3232: frob.docs dispatches on every frob.lang-supported language,
    # not python only -- csharp's XML `<summary>` doc comments already
    # bind to RawSymbol.doc_text (frob.lang._walk_csharp), so a public
    # class's and a public method's doc comments resolve through the same
    # extract_docstrings path python docstrings do.
    src = _FIXTURES / "sample.cs"
    docs = extract_docstrings(src)
    by_symbol = {d.symbol: d for d in docs}
    assert "Frob.Sample.Widget" in by_symbol
    assert by_symbol["Frob.Sample.Widget"].kind == "class"
    assert "Adds two numbers" in by_symbol["Frob.Sample.Widget"].text
    assert "Frob.Sample.Widget.Render" in by_symbol
    assert "Renders the widget" in by_symbol["Frob.Sample.Widget.Render"].text


def test_extract_docstrings_csharp_nested_class_is_skipped(tmp_path):
    # frob:tests src/frob/docs/__init__.py::extract_docstrings kind="unit"
    # frob:ticket T-4519
    # T-4519: pins two DISCLOSED, PRE-EXISTING behaviors on a csharp
    # fixture with a nested type and a property doc comment (neither of
    # which `sample.cs`, T-3232's fixture, exercises) --
    # `_class_qualnames`/`_docstring_for_symbol` deliberately drop a
    # nested class's own docstring (its qualname's owner is another
    # class in the same file, module docstring's namespace-vs-nesting
    # distinction), and `_docstring_for_symbol` has no branch for
    # `SymbolKind.CONST` at all, so a property's `///` doc comment
    # (`_walk_csharp._cs_property_symbol` maps it onto CONST) is never
    # emitted either. Neither is a T-4519 defect -- both predate this
    # ticket and its scope (src/frob/docs/__init__.py, but not a rewrite
    # of the nested/CONST design) -- this test only makes the current
    # behavior visible instead of silently unverified.
    src = _FIXTURES / "csharp" / "nested_property_event.cs"
    docs = extract_docstrings(src)
    by_symbol = {d.symbol: d for d in docs}
    assert "Frob.Sample.Nested.Container" in by_symbol
    assert "container exercising" in by_symbol["Frob.Sample.Nested.Container"].text
    assert "Frob.Sample.Nested.Container.Inner" not in by_symbol
    assert "Frob.Sample.Nested.Container.Total" not in by_symbol


def test_extract_docstrings_parse_failure_returns_empty(tmp_path):
    # frob:tests src/frob/docs/__init__.py::extract_docstrings kind="unit"
    src = tmp_path / "does_not_exist.py"
    assert extract_docstrings(src) == []


def test_extract_docstrings_symbol_filter_narrows_to_one_method(tmp_path):
    # frob:tests src/frob/docs/__init__.py::extract_docstrings kind="unit"
    src = tmp_path / "mod.py"
    src.write_text(
        '"""Module doc."""\n\n\n'
        "class Widget:\n"
        "    def render(self):\n"
        '        """Render it."""\n'
        "        pass\n\n"
        "    def other(self):\n"
        '        """Other thing."""\n'
        "        pass\n"
    )
    docs = extract_docstrings(src, symbol="Widget.render")
    symbols = {d.symbol for d in docs}
    assert symbols == {"Widget.render"}


def test_find_docs_dir_not_found_returns_none(tmp_path):
    # frob:tests src/frob/docs/__init__.py::find_docs_dir kind="unit"
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_docs_dir(nested) is None


def test_overview_no_keyword_match_falls_back_to_all_entries(tmp_path):
    # frob:tests src/frob/docs/__init__.py::overview kind="unit"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "widget.md").write_text("# widget\n\nDescribes the widget module.\n")
    src = tmp_path / "zzzznomatch.py"
    src.write_text("x = 1\n")
    entries = overview(src)
    assert entries
    assert any("widget" in e.heading.lower() for e in entries)


def test_overview_symbol_keyword_narrows_match(tmp_path):
    # frob:tests src/frob/docs/__init__.py::overview kind="unit"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "widget.md").write_text("# widget\n\nDescribes the widget module.\n")
    (docs_dir / "gadget.md").write_text("# gadget\n\nDescribes the gadget module.\n")
    src = tmp_path / "unrelated.py"
    src.write_text("x = 1\n")
    entries = overview(src, symbol="gadget_thing")
    assert entries
    assert all("gadget" in e.heading.lower() for e in entries)


def test_search_tracks_heading_and_joins_surrounding_lines(tmp_path):
    # frob:tests src/frob/docs/__init__.py::search kind="unit"
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "widget.md").write_text(
        "# Widget\n\nbefore line\nthe target line\nafter line\n"
    )
    matches = search("target", docs_dir)
    assert len(matches) == 1
    match = matches[0]
    assert match.heading == "Widget"
    assert "before line" in match.excerpt
    assert "the target line" in match.excerpt
    assert "after line" in match.excerpt


def test_docs_module_integration(tmp_path):
    # frob:tests src/frob/docs kind="integration"
    # Exercises the docs surface together: docstring extraction over a real
    # source file, plus docs-directory discovery, overview, and search over a
    # sibling docs/ tree.
    src = tmp_path / "widget.py"
    src.write_text(
        '"""Widget module."""\n\n\n'
        "def render(value):\n"
        '    """Render the widget value."""\n'
        "    return value\n"
    )
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "widget.md").write_text("# Widget\n\nThe widget renders a value.\n")

    docs = extract_docstrings(src)
    assert any(d.symbol == "render" for d in docs)

    assert find_docs_dir(src) == docs_dir

    entries = overview(src)
    assert any("widget" in e.heading.lower() for e in entries)

    matches = search("renders", docs_dir)
    assert any("renders" in m.excerpt.lower() for m in matches)
