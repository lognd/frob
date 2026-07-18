# frob:waive TEST005 reason="module line coverage 84.3%, debt T-0160"
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError
from typani import Err, ErrorSet, Ok
from typani.result import Result

_DATA_DIR = Path(__file__).parent / "data"


# frob:doc docs/commands/scaffold.md#public-api
class ScaffoldError(ErrorSet):
    UnknownType = "Requested project type is not registered"
    TemplateNotFound = "Template .j2 file is missing from the data directory"
    OutputExists = (
        "One or more output files already exist (use force=True to overwrite)"
    )
    RenderFailed = "Jinja2 raised an error while rendering a template"


@dataclass(frozen=True)
class _ManifestEntry:
    # Template path inside data/ (relative, may include subdirectories)
    template: str
    # Output path relative to the project root; may contain Jinja2 expressions
    output: str


_MANIFESTS: dict[str, list[_ManifestEntry]] = {
    "python-library": [
        _ManifestEntry("shared/python/README.md.j2", "README.md"),
        _ManifestEntry("shared/python/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/python/env.example.j2", ".env.example"),
        _ManifestEntry("shared/python/Makefile.j2", "Makefile"),
        _ManifestEntry("shared/python/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry(
            "shared/python/scripts/bump_version.py.j2", "scripts/bump_version.py"
        ),
        _ManifestEntry("shared/python/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry(
            "types/python-library/__init__.py.j2", "src/{{ project.name }}/__init__.py"
        ),
        _ManifestEntry(
            "shared/python/logging/__init__.py.j2",
            "src/{{ project.name }}/logging/__init__.py",
        ),
        _ManifestEntry(
            "shared/python/logging/config.toml.j2",
            "src/{{ project.name }}/logging/config.toml",
        ),
        _ManifestEntry(
            "shared/python/logging/filter.py.j2",
            "src/{{ project.name }}/logging/filter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/formatter.py.j2",
            "src/{{ project.name }}/logging/formatter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/logger.py.j2",
            "src/{{ project.name }}/logging/logger.py",
        ),
        _ManifestEntry("shared/python/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("shared/python/tests/conftest.py.j2", "tests/conftest.py"),
        _ManifestEntry(
            "shared/python/tests/unit/test_placeholder.py.j2",
            "tests/unit/test_placeholder.py",
        ),
        _ManifestEntry(
            "shared/python/tests/system/test_build.py.j2", "tests/system/test_build.py"
        ),
        _ManifestEntry("shared/python/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/python/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
    ],
    "python-tool": [
        _ManifestEntry("shared/python/README.md.j2", "README.md"),
        _ManifestEntry("shared/python/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/python/env.example.j2", ".env.example"),
        _ManifestEntry("shared/python/Makefile.j2", "Makefile"),
        _ManifestEntry("types/python-tool/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry(
            "shared/python/scripts/bump_version.py.j2", "scripts/bump_version.py"
        ),
        _ManifestEntry("shared/python/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry(
            "types/python-tool/__init__.py.j2", "src/{{ project.name }}/__init__.py"
        ),
        _ManifestEntry(
            "types/python-tool/__main__.py.j2", "src/{{ project.name }}/__main__.py"
        ),
        _ManifestEntry(
            "types/python-tool/app/__init__.py.j2",
            "src/{{ project.name }}/app/__init__.py",
        ),
        _ManifestEntry(
            "types/python-tool/app/app.py.j2", "src/{{ project.name }}/app/app.py"
        ),
        _ManifestEntry(
            "types/python-tool/app/config.py.j2", "src/{{ project.name }}/app/config.py"
        ),
        _ManifestEntry(
            "shared/python/logging/__init__.py.j2",
            "src/{{ project.name }}/logging/__init__.py",
        ),
        _ManifestEntry(
            "shared/python/logging/config.toml.j2",
            "src/{{ project.name }}/logging/config.toml",
        ),
        _ManifestEntry(
            "shared/python/logging/filter.py.j2",
            "src/{{ project.name }}/logging/filter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/formatter.py.j2",
            "src/{{ project.name }}/logging/formatter.py",
        ),
        _ManifestEntry(
            "shared/python/logging/logger.py.j2",
            "src/{{ project.name }}/logging/logger.py",
        ),
        _ManifestEntry("types/python-tool/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("shared/python/tests/conftest.py.j2", "tests/conftest.py"),
        _ManifestEntry(
            "types/python-tool/tests/unit/test_app.py.j2", "tests/unit/test_app.py"
        ),
        _ManifestEntry(
            "types/python-tool/tests/unit/test_main.py.j2", "tests/unit/test_main.py"
        ),
        _ManifestEntry(
            "types/python-tool/tests/unit/test_logging.py.j2",
            "tests/unit/test_logging.py",
        ),
        _ManifestEntry(
            "types/python-tool/tests/system/test_build.py.j2",
            "tests/system/test_build.py",
        ),
        _ManifestEntry("shared/python/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/python/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
        _ManifestEntry(
            "types/python-tool/github/release.yml.j2",
            ".github/workflows/release.yml",
        ),
    ],
    "cpp-library": [
        _ManifestEntry("shared/cpp/README.md.j2", "README.md"),
        _ManifestEntry("shared/cpp/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/cpp/Makefile.j2", "Makefile"),
        _ManifestEntry("shared/cpp/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("shared/cpp/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/cpp-library/CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry(
            "types/cpp-library/cmake/Config.cmake.in.j2",
            "cmake/{{ project.name }}Config.cmake.in",
        ),
        _ManifestEntry("types/cpp-library/src.cpp.j2", "src/{{ project.name }}.cpp"),
        _ManifestEntry(
            "types/cpp-library/include.h.j2", "include/{{ project.name }}.h"
        ),
        _ManifestEntry("shared/cpp/tests/CMakeLists.txt.j2", "tests/CMakeLists.txt"),
        _ManifestEntry(
            "types/cpp-library/tests.cpp.j2", "tests/test_{{ project.name }}.cpp"
        ),
        _ManifestEntry("shared/cpp/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/cpp/github/release.yml.j2", ".github/workflows/release.yml"
        ),
        _ManifestEntry(
            "shared/cpp/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
        _ManifestEntry(
            "shared/cpp/cmake/toolchain-linux-arm64.cmake.j2",
            "cmake/toolchain-linux-arm64.cmake",
        ),
    ],
    "cpp-tool": [
        _ManifestEntry("shared/cpp/README.md.j2", "README.md"),
        _ManifestEntry("shared/cpp/gitignore.j2", ".gitignore"),
        _ManifestEntry("shared/cpp/Makefile.j2", "Makefile"),
        _ManifestEntry("shared/cpp/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("shared/cpp/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/cpp-tool/CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry("types/cpp-tool/src.cpp.j2", "src/{{ project.name }}.cpp"),
        _ManifestEntry("types/cpp-tool/main.cpp.j2", "src/main.cpp"),
        _ManifestEntry("types/cpp-tool/include.h.j2", "include/{{ project.name }}.h"),
        _ManifestEntry("shared/cpp/tests/CMakeLists.txt.j2", "tests/CMakeLists.txt"),
        _ManifestEntry(
            "types/cpp-tool/tests.cpp.j2", "tests/test_{{ project.name }}.cpp"
        ),
        _ManifestEntry("shared/cpp/github/ci.yml.j2", ".github/workflows/ci.yml"),
        _ManifestEntry(
            "shared/cpp/github/release.yml.j2", ".github/workflows/release.yml"
        ),
        _ManifestEntry(
            "shared/cpp/github/branch-protection.yml.j2",
            ".github/workflows/branch-protection.yml",
        ),
        _ManifestEntry(
            "shared/cpp/cmake/toolchain-linux-arm64.cmake.j2",
            "cmake/toolchain-linux-arm64.cmake",
        ),
    ],
    "pybind11-library": [
        _ManifestEntry("shared/pybind11/gitignore.j2", ".gitignore"),
        _ManifestEntry("types/pybind11-library/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry("types/pybind11-library/Makefile.j2", "Makefile"),
        _ManifestEntry("types/pybind11-library/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("shared/cpp/README.md.j2", "README.md"),
        _ManifestEntry("shared/cpp/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/pybind11-library/CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry(
            "types/pybind11-library/src.cpp.j2", "src/{{ project.name }}.cpp"
        ),
        _ManifestEntry(
            "types/pybind11-library/include.h.j2", "include/{{ project.name }}.h"
        ),
        _ManifestEntry("types/pybind11-library/bindings.cpp.j2", "src/bindings.cpp"),
        _ManifestEntry(
            "types/pybind11-library/python/__init__.py.j2",
            "{{ project.name }}/__init__.py",
        ),
        _ManifestEntry(
            "types/pybind11-library/tests/test_bindings.py.j2", "tests/test_bindings.py"
        ),
        _ManifestEntry(
            "types/pybind11-library/github/ci.yml.j2", ".github/workflows/ci.yml"
        ),
    ],
    "pyo3-library": [
        _ManifestEntry("shared/pyo3/gitignore.j2", ".gitignore"),
        _ManifestEntry("types/pyo3-library/pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry("types/pyo3-library/Cargo.toml.j2", "Cargo.toml"),
        _ManifestEntry(
            "types/pyo3-library/rust-toolchain.toml.j2", "rust-toolchain.toml"
        ),
        _ManifestEntry("types/pyo3-library/Makefile.j2", "Makefile"),
        _ManifestEntry("types/pyo3-library/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("types/pyo3-library/README.md.j2", "README.md"),
        _ManifestEntry("types/pyo3-library/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/pyo3-library/crates/Cargo.toml.j2", "crates/Cargo.toml"),
        _ManifestEntry("types/pyo3-library/crates/lib.rs.j2", "crates/src/lib.rs"),
        _ManifestEntry(
            "types/pyo3-library/python/__init__.py.j2",
            "python/{{ project.name }}/__init__.py",
        ),
        _ManifestEntry(
            "types/pyo3-library/tests/test_bindings.py.j2", "tests/test_bindings.py"
        ),
        _ManifestEntry(
            "types/pyo3-library/github/ci.yml.j2", ".github/workflows/ci.yml"
        ),
        _ManifestEntry(
            "types/pyo3-library/github/release.yml.j2",
            ".github/workflows/release.yml",
        ),
    ],
    "web-app": [
        _ManifestEntry("types/web-app/gitignore.j2", ".gitignore"),
        _ManifestEntry("types/web-app/package.json.j2", "package.json"),
        _ManifestEntry("types/web-app/tsconfig.json.j2", "tsconfig.json"),
        _ManifestEntry("types/web-app/prettierrc.json.j2", ".prettierrc.json"),
        _ManifestEntry("types/web-app/eslint.config.js.j2", "eslint.config.js"),
        _ManifestEntry("types/web-app/vite.config.ts.j2", "vite.config.ts"),
        _ManifestEntry("types/web-app/index.html.j2", "index.html"),
        _ManifestEntry("types/web-app/Makefile.j2", "Makefile"),
        _ManifestEntry("types/web-app/frob.toml.j2", "frob.toml"),
        _ManifestEntry("shared/python/tickets.md.j2", "tickets.md"),
        _ManifestEntry("shared/python/gitkeep.j2", "invariants/.gitkeep"),
        _ManifestEntry("types/web-app/README.md.j2", "README.md"),
        _ManifestEntry("types/web-app/docs/index.md.j2", "docs/index.md"),
        _ManifestEntry("types/web-app/src/main.tsx.j2", "src/main.tsx"),
        _ManifestEntry("types/web-app/src/App.tsx.j2", "src/App.tsx"),
        _ManifestEntry("types/web-app/vite-env.d.ts.j2", "src/vite-env.d.ts"),
        _ManifestEntry("types/web-app/tests/setup.ts.j2", "tests/setup.ts"),
        _ManifestEntry(
            "types/web-app/tests/unit/App.test.tsx.j2", "tests/unit/App.test.tsx"
        ),
        _ManifestEntry("types/web-app/github/ci.yml.j2", ".github/workflows/ci.yml"),
    ],
}


# frob:doc docs/commands/scaffold.md#public-api
def list_project_types() -> list[str]:
    return list(_MANIFESTS.keys())


# frob:doc docs/commands/scaffold.md#public-api
# frob:waive TEST005 reason="render_project 74.2% branch cover, debt T-0160"
def render_project(
    project_type: str,
    name: str,
    output_dir: Path,
    *,
    force: bool = False,
) -> Result[list[Path], ScaffoldError]:
    if project_type not in _MANIFESTS:
        return Err(ScaffoldError.UnknownType)

    env = Environment(
        loader=FileSystemLoader(str(_DATA_DIR)),
        keep_trailing_newline=True,
    )
    ctx = {"project": {"name": name, "type": project_type}}

    entries = _MANIFESTS[project_type]

    resolved: list[tuple[_ManifestEntry, Path]] = []
    for entry in entries:
        try:
            out_rel = env.from_string(entry.output).render(ctx)
        except Exception:
            return Err(ScaffoldError.RenderFailed)
        out_path = output_dir / out_rel
        resolved.append((entry, out_path))

    if not force:
        for _, out_path in resolved:
            if out_path.exists():
                return Err(ScaffoldError.OutputExists)

    written: list[Path] = []
    for entry, out_path in resolved:
        try:
            tmpl = env.get_template(entry.template)
        except TemplateNotFound:
            return Err(ScaffoldError.TemplateNotFound)
        try:
            content = tmpl.render(ctx)
        except TemplateSyntaxError:
            return Err(ScaffoldError.RenderFailed)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content)
        written.append(out_path)

    return Ok(written)
