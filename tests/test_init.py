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


def test_list_project_types_includes_cpp():
    types = list_project_types()
    assert "cpp-library" in types
    assert "cpp-tool" in types


def test_render_cpp_library_creates_expected_files(tmp_path):
    result = render_project("cpp-library", "mylib", tmp_path)
    assert result.is_ok, result
    created = result.danger_ok
    names = [p.name for p in created]
    assert "CMakeLists.txt" in names
    assert "mylib.h" in names
    assert "mylib.cpp" in names
    assert "test_mylib.cpp" in names
    assert "README.md" in names
    assert ".gitignore" in names


def test_render_cpp_library_name_substituted(tmp_path):
    render_project("cpp-library", "mylib", tmp_path)
    cmake = (tmp_path / "CMakeLists.txt").read_text()
    assert "mylib" in cmake
    header = (tmp_path / "include" / "mylib.h").read_text()
    assert "#pragma once" in header
    src = (tmp_path / "src" / "mylib.cpp").read_text()
    assert '#include "mylib.h"' in src


def test_render_cpp_tool_creates_expected_files(tmp_path):
    result = render_project("cpp-tool", "mytool", tmp_path)
    assert result.is_ok, result
    created = result.danger_ok
    names = [p.name for p in created]
    assert "CMakeLists.txt" in names
    assert "main.cpp" in names
    assert "mytool.h" in names
    assert "mytool.cpp" in names
    assert "test_mytool.cpp" in names
    assert "README.md" in names
    assert ".gitignore" in names


def test_render_cpp_tool_name_substituted(tmp_path):
    render_project("cpp-tool", "mytool", tmp_path)
    cmake = (tmp_path / "CMakeLists.txt").read_text()
    assert "mytool" in cmake
    assert "mytool_lib" in cmake
    main = (tmp_path / "src" / "main.cpp").read_text()
    assert "EXIT_SUCCESS" in main
    assert '#include "mytool.h"' in main


def test_render_cpp_library_tests_cmake(tmp_path):
    render_project("cpp-library", "mylib", tmp_path)
    tests_cmake = (tmp_path / "tests" / "CMakeLists.txt").read_text()
    assert "googletest" in tests_cmake
    assert "test_mylib" in tests_cmake


def test_render_cpp_tool_tests_cmake(tmp_path):
    render_project("cpp-tool", "mytool", tmp_path)
    tests_cmake = (tmp_path / "tests" / "CMakeLists.txt").read_text()
    assert "googletest" in tests_cmake
    assert "test_mytool" in tests_cmake
