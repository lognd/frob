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
