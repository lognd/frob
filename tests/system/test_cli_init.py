"""
End-to-end tests for `frob init`.

Each project type is scaffolded exactly once (via a session-scoped fixture) and
all file/content checks are bundled into a single test per type.
"""

from tests.system.conftest import run


def _scaffold(tmp_path, project_type, name):
    r = run(
        "init",
        "new",
        project_type,
        name,
        "--output",
        str(tmp_path),
        cwd=str(tmp_path),
    )
    assert r.returncode == 0, r.stderr
    return tmp_path


# ---------------------------------------------------------------------------
# frob init list
# ---------------------------------------------------------------------------


def test_list_exit_zero():
    r = run("init", "list")
    assert r.returncode == 0


def test_list_shows_all_types():
    r = run("init", "list")
    assert r.returncode == 0
    for t in (
        "python-library",
        "python-tool",
        "cpp-library",
        "cpp-tool",
        "pybind11-library",
        "pyo3-library",
    ):
        assert t in r.stdout


# ---------------------------------------------------------------------------
# python-tool
# ---------------------------------------------------------------------------


def test_python_tool(tmp_path):
    p = _scaffold(tmp_path, "python-tool", "myapp")

    # structure
    assert (p / "pyproject.toml").exists()
    assert (p / "Makefile").exists()
    assert (p / ".gitignore").exists()
    assert (p / "README.md").exists()
    assert (p / "docs" / "index.md").exists()
    assert (p / "src" / "myapp" / "__init__.py").exists()
    assert (p / "src" / "myapp" / "__main__.py").exists()
    assert (p / "src" / "myapp" / "logging" / "__init__.py").exists()
    assert (p / "tests" / "conftest.py").exists()
    assert (p / "tests" / "unit" / "test_placeholder.py").exists()
    assert (p / "tests" / "system" / "test_build.py").exists()
    assert (p / ".github" / "workflows" / "ci.yml").exists()
    assert (p / ".github" / "workflows" / "branch-protection.yml").exists()

    # content
    pyproject = (p / "pyproject.toml").read_text()
    assert 'name = "myapp"' in pyproject
    assert 'version = "0.1.0"' in pyproject

    main = (p / "src" / "myapp" / "__main__.py").read_text()
    assert "def main" in main


# ---------------------------------------------------------------------------
# python-library
# ---------------------------------------------------------------------------


def test_python_library(tmp_path):
    p = _scaffold(tmp_path, "python-library", "mylib")

    assert (p / "pyproject.toml").exists()
    assert (p / "Makefile").exists()
    assert (p / ".gitignore").exists()
    assert (p / "README.md").exists()
    assert (p / "docs" / "index.md").exists()
    assert (p / "src" / "mylib" / "__init__.py").exists()
    assert (p / "src" / "mylib" / "logging" / "__init__.py").exists()
    assert (p / "tests" / "conftest.py").exists()
    assert (p / "tests" / "unit" / "test_placeholder.py").exists()
    assert (p / ".github" / "workflows" / "ci.yml").exists()
    assert (p / ".github" / "workflows" / "branch-protection.yml").exists()

    pyproject = (p / "pyproject.toml").read_text()
    assert 'name = "mylib"' in pyproject
    assert 'version = "0.1.0"' in pyproject


# ---------------------------------------------------------------------------
# cpp-library
# ---------------------------------------------------------------------------


def test_cpp_library(tmp_path):
    p = _scaffold(tmp_path, "cpp-library", "mylib")

    assert (p / "CMakeLists.txt").exists()
    assert (p / "Makefile").exists()
    assert (p / ".gitignore").exists()
    assert (p / "README.md").exists()
    assert (p / "docs" / "index.md").exists()
    assert (p / "include" / "mylib.h").exists()
    assert (p / "src" / "mylib.cpp").exists()
    assert (p / "tests" / "CMakeLists.txt").exists()
    assert (p / ".github" / "workflows" / "ci.yml").exists()
    assert (p / ".github" / "workflows" / "branch-protection.yml").exists()
    assert (p / ".github" / "workflows" / "release.yml").exists()
    assert (p / "cmake" / "toolchain-linux-arm64.cmake").exists()


# ---------------------------------------------------------------------------
# cpp-tool
# ---------------------------------------------------------------------------


def test_cpp_tool(tmp_path):
    p = _scaffold(tmp_path, "cpp-tool", "mytool")

    assert (p / "CMakeLists.txt").exists()
    assert (p / "Makefile").exists()
    assert (p / "include" / "mytool.h").exists()
    assert (p / "src" / "mytool.cpp").exists()
    assert (p / "src" / "main.cpp").exists()
    assert (p / "tests" / "CMakeLists.txt").exists()
    assert (p / ".github" / "workflows" / "ci.yml").exists()
    assert (p / ".github" / "workflows" / "release.yml").exists()


# ---------------------------------------------------------------------------
# double-init and --force
# ---------------------------------------------------------------------------


def test_double_init_without_force_fails(tmp_path):
    _scaffold(tmp_path, "python-library", "mylib")
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
    _scaffold(tmp_path, "python-library", "mylib")
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
