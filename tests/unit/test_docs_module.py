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


# frob:waive PERF003 reason="fixture-write helper loop plus sibling equality asserts over docs search results; not a nested join"
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
