"""End-to-end tests for `frob edit`."""

from tests.system.conftest import run

PY_SRC = """\
def foo(x: int) -> int:
    return x + 1


def bar(y: str) -> str:
    return y.upper()


class MyClass:
    def method(self) -> None:
        pass
"""


class TestEditIsolate:
    def _py_file(self, tmp_path):
        p = tmp_path / "mod.py"
        p.write_text(PY_SRC)
        return p

    def test_isolate_function(self, tmp_path):
        p = self._py_file(tmp_path)
        r = run("edit", str(p), "foo")
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "def foo" in out

    def test_isolate_class(self, tmp_path):
        p = self._py_file(tmp_path)
        r = run("edit", str(p), "MyClass")
        assert r.returncode == 0
        assert "class MyClass" in (r.stdout + r.stderr)

    def test_isolate_method(self, tmp_path):
        p = self._py_file(tmp_path)
        r = run("edit", str(p), "MyClass.method")
        assert r.returncode == 0
        assert "def method" in (r.stdout + r.stderr)

    def test_not_found(self, tmp_path):
        p = self._py_file(tmp_path)
        r = run("edit", str(p), "missing_fn")
        assert r.returncode != 0

    def test_shows_line_numbers(self, tmp_path):
        p = self._py_file(tmp_path)
        r = run("edit", str(p), "foo")
        out = r.stdout + r.stderr
        assert "L1" in out or "[L" in out


class TestEditReplace:
    def _py_file(self, tmp_path):
        p = tmp_path / "mod.py"
        p.write_text(PY_SRC)
        return p

    def test_replace_function(self, tmp_path):
        p = self._py_file(tmp_path)
        new_fn = "def foo(x: int) -> int:\n    return x * 100\n"
        r = run("edit", str(p), "foo", "--replace", input=new_fn)
        assert r.returncode == 0
        assert "return x * 100" in p.read_text()

    def test_replace_preserves_other_symbols(self, tmp_path):
        p = self._py_file(tmp_path)
        new_fn = "def foo(x: int) -> int:\n    return 0\n"
        run("edit", str(p), "foo", "--replace", input=new_fn)
        content = p.read_text()
        assert "def bar" in content
        assert "class MyClass" in content

    def test_replace_method(self, tmp_path):
        p = self._py_file(tmp_path)
        new_method = "    def method(self) -> None:\n        pass  # replaced\n"
        r = run("edit", str(p), "MyClass.method", "--replace", input=new_method)
        assert r.returncode == 0
        assert "# replaced" in p.read_text()
