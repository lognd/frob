"""Unit tests for frob.docs: docstring extraction and docs-directory search."""

from __future__ import annotations

from frob.docs import extract_docstrings, find_docs_dir, overview, search


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
    # frob:tests src/frob/docs/__init__.py::extract_docstrings kind="unit"
    src = tmp_path / "mod.rs"
    src.write_text('/// A rust doc comment.\nfn foo() {}\n')
    assert extract_docstrings(src) == []


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
        '    def render(self):\n'
        '        """Render it."""\n'
        "        pass\n\n"
        '    def other(self):\n'
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
