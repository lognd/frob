"""Tests for frob.lang -- uniform tree-sitter parsing (docs/lang.md)."""

from __future__ import annotations

from pathlib import Path

from frob.lang import LangError, SymbolKind, parse_file, supported_languages

_FIXTURES = Path(__file__).parent / "fixtures" / "lang"


def _write(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text)
    return path


def _symbol(pf, qualname: str):
    return next(s for s in pf.symbols if s.qualname == qualname)


class TestParsePython:
    def test_symbols_and_nesting(self) -> None:
        # frob:tests src/frob/lang/__init__.py::parse_file
        pf = parse_file(_FIXTURES / "sample.py").danger_ok
        assert pf.language == "python"
        names = {s.qualname for s in pf.symbols}
        assert {
            "GraphStore",
            "GraphStore.load",
            "GraphStore._private_helper",
            "top_level",
        } <= names
        cls = _symbol(pf, "GraphStore")
        assert cls.kind == SymbolKind.CLASS
        method = _symbol(pf, "GraphStore.load")
        assert method.kind == SymbolKind.METHOD
        assert method.public is True
        private = _symbol(pf, "GraphStore._private_helper")
        assert private.public is False

    def test_decorator_in_sig_tokens(self) -> None:
        pf = parse_file(_FIXTURES / "sample.py").danger_ok
        top = _symbol(pf, "top_level")
        assert "decorator" in top.sig_tokens

    def test_docstring_in_doc_text_and_excluded_from_body(self) -> None:
        pf = parse_file(_FIXTURES / "sample.py").danger_ok
        top = _symbol(pf, "top_level")
        assert top.doc_text == "Add two numbers."
        assert not any("Add two numbers" in t for t in top.body_tokens)

    def test_comments_bind_enclosing_and_following(self) -> None:
        pf = parse_file(_FIXTURES / "sample.py").danger_ok
        comments = {c.text.strip(): c for c in pf.comments}
        assert "read the bytes" in comments
        assert comments["read the bytes"].enclosing == "GraphStore.load"
        assert "sum them" in comments
        assert comments["sum them"].enclosing == "top_level"

    def test_content_hash_changes_on_any_byte_change(self, tmp_path: Path) -> None:
        base = (_FIXTURES / "sample.py").read_text()
        p1 = _write(tmp_path, "a.py", base)
        p2 = _write(tmp_path, "b.py", base + "\n")
        h1 = parse_file(p1).danger_ok.content_hash
        h2 = parse_file(p2).danger_ok.content_hash
        assert h1 != h2
        assert len(h1) == 64


class TestFormattingInsensitivity:
    def _base(self) -> str:
        return (_FIXTURES / "sample.py").read_text()

    def test_reformat_preserves_tokens(self, tmp_path: Path) -> None:
        base = self._base()
        reformatted = (
            base.replace("    def load", "    def   load").replace(
                "return bool(data)", "return   bool(data)"
            )
            + "\n\n\n"
        )
        orig = parse_file(_write(tmp_path, "orig.py", base)).danger_ok
        rf = parse_file(_write(tmp_path, "rf.py", reformatted)).danger_ok
        o = _symbol(orig, "GraphStore.load")
        r = _symbol(rf, "GraphStore.load")
        assert o.sig_tokens == r.sig_tokens
        assert o.body_tokens == r.body_tokens

    def test_param_rename_changes_sig_only(self, tmp_path: Path) -> None:
        base = self._base()
        renamed = base.replace(
            "def load(self, path: str)", "def load(self, filepath: str)"
        )
        orig = parse_file(_write(tmp_path, "orig.py", base)).danger_ok
        rn = parse_file(_write(tmp_path, "rn.py", renamed)).danger_ok
        o = _symbol(orig, "GraphStore.load")
        r = _symbol(rn, "GraphStore.load")
        assert o.sig_tokens != r.sig_tokens
        assert o.body_tokens == r.body_tokens

    def test_body_edit_changes_body_only(self, tmp_path: Path) -> None:
        base = self._base()
        edited = base.replace("return bool(data)", "return data is not None")
        orig = parse_file(_write(tmp_path, "orig.py", base)).danger_ok
        ed = parse_file(_write(tmp_path, "ed.py", edited)).danger_ok
        o = _symbol(orig, "GraphStore.load")
        e = _symbol(ed, "GraphStore.load")
        assert o.sig_tokens == e.sig_tokens
        assert o.body_tokens != e.body_tokens

    def test_docstring_edit_changes_only_doc_text(self, tmp_path: Path) -> None:
        base = self._base()
        edited = base.replace(
            '"""Load a file from disk."""',
            '"""Load a file from the given disk path."""',
        )
        orig = parse_file(_write(tmp_path, "orig.py", base)).danger_ok
        ed = parse_file(_write(tmp_path, "ed.py", edited)).danger_ok
        o = _symbol(orig, "GraphStore.load")
        e = _symbol(ed, "GraphStore.load")
        assert o.sig_tokens == e.sig_tokens
        assert o.body_tokens == e.body_tokens
        assert o.doc_text != e.doc_text


class TestParseTsRustCppC:
    def test_typescript(self) -> None:
        pf = parse_file(_FIXTURES / "sample.ts").danger_ok
        assert pf.language == "typescript"
        fn = _symbol(pf, "add")
        assert fn.kind == SymbolKind.FUNCTION
        assert fn.public is True
        assert fn.doc_text == "Adds two numbers."
        cls = _symbol(pf, "Widget")
        assert cls.kind == SymbolKind.CLASS
        method = _symbol(pf, "Widget.render")
        assert method.kind == SymbolKind.METHOD
        assert method.public is True
        hidden = _symbol(pf, "Widget.hidden")
        assert hidden.public is False
        const = _symbol(pf, "MAX_WIDGETS")
        assert const.kind == SymbolKind.CONST
        shape = _symbol(pf, "Shape")
        assert shape.kind == SymbolKind.TYPE
        assert any("sum them" in c.text for c in pf.comments)

    def test_rust(self) -> None:
        pf = parse_file(_FIXTURES / "sample.rs").danger_ok
        assert pf.language == "rust"
        fn = _symbol(pf, "add")
        assert fn.kind == SymbolKind.FUNCTION
        assert fn.public is True
        assert fn.doc_text == "Adds two numbers."
        cls = _symbol(pf, "Widget")
        assert cls.kind == SymbolKind.CLASS
        method = _symbol(pf, "Widget.render")
        assert method.kind == SymbolKind.METHOD
        assert method.public is True
        hidden = _symbol(pf, "Widget.hidden")
        assert hidden.public is False
        const = _symbol(pf, "MAX_WIDGETS")
        assert const.kind == SymbolKind.CONST
        assert any("sum them" in c.text for c in pf.comments)

    def test_rust_pyo3_export_is_public_without_pub(self, tmp_path: Path) -> None:
        # A #[pyfunction]/#[pymodule]/#[pymethods] item is the crate's real
        # Python-facing public API even without a `pub` keyword, so frob must
        # count it as public (else COV001 silently skips the whole FFI crate).
        source = (
            "#[pyfunction]\n"
            "fn exported_fn(x: i64) -> i64 { x + 1 }\n"
            "\n"
            "fn internal_helper(x: i64) -> i64 { x - 1 }\n"
            "\n"
            "#[pymethods]\n"
            "impl Widget {\n"
            "    fn exported_method(&self) -> i64 { 0 }\n"
            "}\n"
            "\n"
            "#[pymodule]\n"
            "fn my_core(m: &Bound<'_, PyModule>) -> PyResult<()> { Ok(()) }\n"
        )
        pf = parse_file(_write(tmp_path, "core.rs", source)).danger_ok
        assert _symbol(pf, "exported_fn").public is True
        assert _symbol(pf, "internal_helper").public is False
        assert _symbol(pf, "Widget.exported_method").public is True
        assert _symbol(pf, "my_core").public is True

    def test_cpp(self) -> None:
        pf = parse_file(_FIXTURES / "sample.cpp").danger_ok
        assert pf.language == "cpp"
        fn = _symbol(pf, "add")
        assert fn.kind == SymbolKind.FUNCTION
        assert fn.public is True
        cls = _symbol(pf, "Widget")
        assert cls.kind == SymbolKind.CLASS
        method = _symbol(pf, "Widget.render")
        assert method.public is True
        hidden = _symbol(pf, "Widget.hidden")
        assert hidden.public is False
        const = _symbol(pf, "MAX_WIDGETS")
        assert const.kind == SymbolKind.CONST
        assert any("sum them" in c.text for c in pf.comments)

    def test_c(self) -> None:
        pf = parse_file(_FIXTURES / "sample.c").danger_ok
        assert pf.language == "c"
        fn = _symbol(pf, "add")
        assert fn.kind == SymbolKind.FUNCTION
        assert fn.public is True
        hidden = _symbol(pf, "hidden")
        assert hidden.public is False
        const = _symbol(pf, "MAX_WIDGETS")
        assert const.kind == SymbolKind.CONST
        assert any("sum them" in c.text for c in pf.comments)


class TestErrors:
    def test_unsupported_extension(self, tmp_path: Path) -> None:
        path = _write(tmp_path, "x.xyz", "whatever")
        result = parse_file(path)
        assert result.is_err
        assert result.danger_err == LangError.UnsupportedLanguage

    def test_unreadable_path(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.py"
        result = parse_file(missing)
        assert result.is_err
        assert result.danger_err == LangError.IoFailed

    def test_syntax_error_yields_partial_symbols(self) -> None:
        result = parse_file(_FIXTURES / "broken.py")
        assert result.is_ok
        pf = result.danger_ok
        names = {s.qualname for s in pf.symbols}
        assert "good_one" in names

    def test_supported_languages(self) -> None:
        # frob:tests src/frob/lang/__init__.py::supported_languages
        langs = supported_languages()
        assert {"python", "typescript", "rust", "c", "cpp"} <= langs


def test_lang_pipeline_integration(tmp_path: Path) -> None:
    # frob:tests src/frob/lang kind="integration"
    # Exercises the whole lang surface together: symbol/comment extraction
    # (the per-language walkers via parse_file), import extraction, and
    # identifier iteration must agree on one real source file.
    from frob.lang import extract_imports, iter_identifiers, parse_file

    src = _write(
        tmp_path,
        "mod.py",
        '"""Module doc."""\n'
        "import os\n"
        "from pathlib import Path\n\n"
        "class Widget:\n"
        '    """A widget."""\n\n'
        "    def render(self, value: int) -> str:\n"
        "        # frob:doc docs/x.md#render\n"
        "        return str(value)\n",
    )

    parsed = parse_file(src).danger_ok
    names = {s.qualname for s in parsed.symbols}
    assert {"Widget", "Widget.render"} <= names
    # the directive comment binds to its enclosing method
    directive = next(c for c in parsed.comments if "frob:doc" in c.text)
    assert directive.enclosing == "Widget.render"

    imports = extract_imports(src).danger_ok
    assert "os" in imports and "pathlib" in imports

    idents = iter_identifiers(src).danger_ok
    assert any(name == "Widget" for name, _line in idents)
