"""Unit tests for frob.edit."""

from pathlib import Path

import pytest

from frob.edit import EditError, IsolatedSymbol, isolate, replace


PY_SRC = """\
def foo(x: int) -> int:
    return x + 1


def bar(y: str) -> str:
    return y.upper()


class MyClass:
    def method(self) -> None:
        pass

    def _private(self) -> int:
        return 0
"""


class TestIsolate:
    def _file(self, tmp_path: Path) -> Path:
        p = tmp_path / "mod.py"
        p.write_text(PY_SRC)
        return p

    def test_isolate_function(self, tmp_path):
        p = self._file(tmp_path)
        result = isolate(p, "foo")
        assert result.is_ok
        iso = result.danger_ok
        assert iso.symbol == "foo"
        assert "def foo" in iso.source
        assert iso.start_line == 1

    def test_isolate_second_function(self, tmp_path):
        p = self._file(tmp_path)
        result = isolate(p, "bar")
        assert result.is_ok
        assert "def bar" in result.danger_ok.source

    def test_isolate_class(self, tmp_path):
        p = self._file(tmp_path)
        result = isolate(p, "MyClass")
        assert result.is_ok
        assert "class MyClass" in result.danger_ok.source

    def test_isolate_method(self, tmp_path):
        p = self._file(tmp_path)
        result = isolate(p, "MyClass.method")
        assert result.is_ok
        assert "def method" in result.danger_ok.source

    def test_isolate_private_method(self, tmp_path):
        p = self._file(tmp_path)
        result = isolate(p, "MyClass._private")
        assert result.is_ok
        assert "def _private" in result.danger_ok.source

    def test_symbol_not_found(self, tmp_path):
        p = self._file(tmp_path)
        result = isolate(p, "nonexistent")
        assert result.is_err
        assert result.danger_err == EditError.SymbolNotFound

    def test_unsupported_file(self, tmp_path):
        p = tmp_path / "file.txt"
        p.write_text("hello")
        result = isolate(p, "foo")
        assert result.is_err
        assert result.danger_err == EditError.UnsupportedFile

    def test_line_numbers_are_1_based(self, tmp_path):
        p = self._file(tmp_path)
        result = isolate(p, "foo")
        assert result.danger_ok.start_line >= 1
        assert result.danger_ok.end_line >= result.danger_ok.start_line


class TestReplace:
    def _file(self, tmp_path: Path, src: str | None = None) -> Path:
        p = tmp_path / "mod.py"
        p.write_text(src or PY_SRC)
        return p

    def test_replace_function_body(self, tmp_path):
        p = self._file(tmp_path)
        new_src = "def foo(x: int) -> int:\n    return x * 2\n"
        result = replace(p, "foo", new_src)
        assert result.is_ok
        content = p.read_text()
        assert "return x * 2" in content
        assert "return x + 1" not in content

    def test_replace_preserves_other_functions(self, tmp_path):
        p = self._file(tmp_path)
        new_src = "def foo(x: int) -> int:\n    return x * 2\n"
        replace(p, "foo", new_src)
        content = p.read_text()
        assert "def bar" in content
        assert "class MyClass" in content

    def test_replace_method(self, tmp_path):
        p = self._file(tmp_path)
        new_src = "    def method(self) -> None:\n        print('replaced')\n"
        result = replace(p, "MyClass.method", new_src)
        assert result.is_ok
        assert "print('replaced')" in p.read_text()

    def test_replace_not_found(self, tmp_path):
        p = self._file(tmp_path)
        result = replace(p, "nonexistent", "def nonexistent(): ...\n")
        assert result.is_err
        assert result.danger_err == EditError.SymbolNotFound

    def test_replace_roundtrip(self, tmp_path):
        p = self._file(tmp_path)
        iso = isolate(p, "foo").danger_ok
        new_body = iso.source.replace("return x + 1", "return x + 99")
        replace(p, "foo", new_body)
        iso2 = isolate(p, "foo").danger_ok
        assert "return x + 99" in iso2.source
