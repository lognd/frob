"""
End-to-end tests for `frob init`.
"""


import pytest

from tests.system.conftest import run

# ---------------------------------------------------------------------------
# frob init list
# ---------------------------------------------------------------------------


def test_list_exit_zero():
    r = run("init", "list")
    assert r.returncode == 0


def test_list_shows_python_library():
    r = run("init", "list")
    assert "python-library" in r.stdout


def test_list_shows_python_tool():
    r = run("init", "list")
    assert "python-tool" in r.stdout


def test_list_shows_cpp_library():
    r = run("init", "list")
    assert "cpp-library" in r.stdout


def test_list_shows_cpp_tool():
    r = run("init", "list")
    assert "cpp-tool" in r.stdout


# ---------------------------------------------------------------------------
# frob init new python-tool myapp
# ---------------------------------------------------------------------------


@pytest.fixture
def python_tool_project(tmp_path):
    r = run(
        "init",
        "new",
        "python-tool",
        "myapp",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode == 0
    return tmp_path


def test_python_tool_exit_zero(tmp_path):
    r = run(
        "init",
        "new",
        "python-tool",
        "myapp",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode == 0


def test_python_tool_pyproject_exists(python_tool_project):
    assert (python_tool_project / "pyproject.toml").exists()


def test_python_tool_makefile_exists(python_tool_project):
    assert (python_tool_project / "Makefile").exists()


def test_python_tool_gitignore_exists(python_tool_project):
    assert (python_tool_project / ".gitignore").exists()


def test_python_tool_readme_exists(python_tool_project):
    assert (python_tool_project / "README.md").exists()


def test_python_tool_src_init_exists(python_tool_project):
    assert (python_tool_project / "src" / "myapp" / "__init__.py").exists()


def test_python_tool_src_main_exists(python_tool_project):
    assert (python_tool_project / "src" / "myapp" / "__main__.py").exists()


def test_python_tool_logging_init_exists(python_tool_project):
    assert (python_tool_project / "src" / "myapp" / "logging" / "__init__.py").exists()


def test_python_tool_docs_exists(python_tool_project):
    assert (python_tool_project / "docs" / "index.md").exists()


def test_python_tool_tests_conftest_exists(python_tool_project):
    assert (python_tool_project / "tests" / "conftest.py").exists()


def test_python_tool_unit_test_placeholder_exists(python_tool_project):
    assert (python_tool_project / "tests" / "unit" / "test_placeholder.py").exists()


def test_python_tool_system_test_build_exists(python_tool_project):
    assert (python_tool_project / "tests" / "system" / "test_build.py").exists()


def test_python_tool_ci_workflow_exists(python_tool_project):
    assert (python_tool_project / ".github" / "workflows" / "ci.yml").exists()


def test_python_tool_branch_protection_workflow_exists(python_tool_project):
    assert (
        python_tool_project / ".github" / "workflows" / "branch-protection.yml"
    ).exists()


def test_python_tool_pyproject_contains_name(python_tool_project):
    content = (python_tool_project / "pyproject.toml").read_text()
    assert 'name = "myapp"' in content


def test_python_tool_pyproject_contains_version(python_tool_project):
    content = (python_tool_project / "pyproject.toml").read_text()
    assert 'version = "0.1.0"' in content


def test_python_tool_main_contains_def_main(python_tool_project):
    content = (python_tool_project / "src" / "myapp" / "__main__.py").read_text()
    assert "def main" in content


# ---------------------------------------------------------------------------
# frob init new python-library mylib
# ---------------------------------------------------------------------------


@pytest.fixture
def python_lib_project(tmp_path):
    r = run(
        "init",
        "new",
        "python-library",
        "mylib",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode == 0
    return tmp_path


def test_python_library_exit_zero(tmp_path):
    r = run(
        "init",
        "new",
        "python-library",
        "mylib",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode == 0


def test_python_library_pyproject_exists(python_lib_project):
    assert (python_lib_project / "pyproject.toml").exists()


def test_python_library_src_init_exists(python_lib_project):
    assert (python_lib_project / "src" / "mylib" / "__init__.py").exists()


def test_python_library_pyproject_contains_name(python_lib_project):
    content = (python_lib_project / "pyproject.toml").read_text()
    assert "mylib" in content


# ---------------------------------------------------------------------------
# frob init new cpp-library mylib
# ---------------------------------------------------------------------------


@pytest.fixture
def cpp_lib_project(tmp_path):
    r = run(
        "init",
        "new",
        "cpp-library",
        "mylib",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode == 0
    return tmp_path


def test_cpp_library_exit_zero(tmp_path):
    r = run(
        "init",
        "new",
        "cpp-library",
        "mylib",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode == 0


def test_cpp_library_cmake_exists(cpp_lib_project):
    assert (cpp_lib_project / "CMakeLists.txt").exists()


def test_cpp_library_ci_workflow_exists(cpp_lib_project):
    assert (cpp_lib_project / ".github" / "workflows" / "ci.yml").exists()


def test_cpp_library_branch_protection_exists(cpp_lib_project):
    assert (
        cpp_lib_project / ".github" / "workflows" / "branch-protection.yml"
    ).exists()


def test_cpp_library_header_exists(cpp_lib_project):
    assert (cpp_lib_project / "include" / "mylib.h").exists()


def test_cpp_library_source_exists(cpp_lib_project):
    assert (cpp_lib_project / "src" / "mylib.cpp").exists()


# ---------------------------------------------------------------------------
# Double-init and --force
# ---------------------------------------------------------------------------


def test_double_init_without_force_fails(tmp_path):
    run(
        "init",
        "new",
        "python-library",
        "mylib",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    r = run(
        "init",
        "new",
        "python-library",
        "mylib",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode != 0


def test_double_init_with_force_succeeds(tmp_path):
    run(
        "init",
        "new",
        "python-library",
        "mylib",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    r = run(
        "init",
        "new",
        "python-library",
        "mylib",
        "--output",
        str(tmp_path),
        "--force",
        cwd=str(tmp_path),
    )
    assert r.returncode == 0


# ---------------------------------------------------------------------------
# Unknown project type
# ---------------------------------------------------------------------------


def test_unknown_type_exits_nonzero(tmp_path):
    r = run(
        "init",
        "new",
        "does-not-exist",
        "proj",
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode != 0
