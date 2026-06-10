import pytest
from pathlib import Path

from frob.init.project import render_project, list_project_types, InitError


def test_list_project_types():
    types = list_project_types()
    assert "python-library" in types
    assert "python-tool" in types


def test_render_unknown_type(tmp_path):
    result = render_project("does-not-exist", "myproject", tmp_path)
    assert result.is_err
    assert result.danger_err == InitError.UnknownType


def test_render_python_library_creates_files(tmp_path):
    result = render_project("python-library", "mylib", tmp_path)
    assert result.is_ok, result
    created = result.danger_ok
    assert any(p.name == "pyproject.toml" for p in created)


def test_render_python_tool_creates_files(tmp_path):
    result = render_project("python-tool", "mytool", tmp_path)
    assert result.is_ok, result
    created = result.danger_ok
    names = [p.name for p in created]
    assert "pyproject.toml" in names
    assert "__main__.py" in names


def test_render_project_name_in_output(tmp_path):
    render_project("python-library", "coolproject", tmp_path)
    toml = (tmp_path / "pyproject.toml").read_text()
    assert "coolproject" in toml


def test_render_output_exists_returns_error(tmp_path):
    render_project("python-library", "mylib", tmp_path)
    result = render_project("python-library", "mylib", tmp_path)
    assert result.is_err
    assert result.danger_err == InitError.OutputExists


def test_render_output_exists_force_overwrites(tmp_path):
    render_project("python-library", "mylib", tmp_path)
    result = render_project("python-library", "mylib", tmp_path, force=True)
    assert result.is_ok
