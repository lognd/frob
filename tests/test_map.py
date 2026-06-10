import pytest
from pathlib import Path

from frob.map import map_project


@pytest.fixture
def project(tmp_path, py_sample, cpp_sample):
    (tmp_path / "foo.py").write_bytes(py_sample)
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "bar.cpp").write_bytes(cpp_sample)
    return tmp_path


def test_map_finds_all_files(project):
    result = map_project(project)
    paths = [f.path for f in result.files]
    assert any("foo.py" in p for p in paths)
    assert any("bar.cpp" in p for p in paths)


def test_map_totals(project):
    result = map_project(project)
    assert result.total_files == 2
    assert result.total_lines > 0


def test_map_symbols_populated(project):
    result = map_project(project)
    py_node = next(f for f in result.files if f.path.endswith("foo.py"))
    assert "helper" in py_node.symbols or "MyClass" in py_node.symbols


def test_map_depth_limits_recursion(project):
    result = map_project(project, depth=0)
    paths = [f.path for f in result.files]
    # depth=0 means only files directly in root, no subdirectories
    assert any("foo.py" in p for p in paths)
    assert not any("bar.cpp" in p for p in paths)


def test_map_as_text(project):
    result = map_project(project)
    text = result.as_text()
    assert "foo.py" in text
    assert "bar.cpp" in text
    assert "L" in text


def test_map_as_json(project):
    import json
    result = map_project(project)
    data = json.loads(result.as_json())
    assert data["total_files"] == 2
    assert isinstance(data["files"], list)
