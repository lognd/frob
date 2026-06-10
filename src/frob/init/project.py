from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, TemplateNotFound, TemplateSyntaxError
from typani import ErrorSet, Ok, Err
from typani.result import Result

_DATA_DIR = Path(__file__).parent / "data"


class InitError(ErrorSet):
    UnknownType = "Requested project type is not registered"
    TemplateNotFound = "Template .j2 file is missing from the data directory"
    OutputExists = "One or more output files already exist (use force=True to overwrite)"
    RenderFailed = "Jinja2 raised an error while rendering a template"


@dataclass(frozen=True)
class _ManifestEntry:
    # Template filename inside data/ (without .j2)
    template: str
    # Output path relative to the project root; may contain Jinja2 expressions
    output: str


_MANIFESTS: dict[str, list[_ManifestEntry]] = {
    "python-library": [
        _ManifestEntry("README.md.j2", "README.md"),
        _ManifestEntry("python_shared.gitignore.j2", ".gitignore"),
        _ManifestEntry("python_shared.Makefile.j2", "Makefile"),
        _ManifestEntry("pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry("python_lib.__init__.py.j2", "src/{{ project.name }}/__init__.py"),
        _ManifestEntry("python_shared.logging.__init__.py.j2", "src/{{ project.name }}/logging/__init__.py"),
        _ManifestEntry("python_shared.logging.config.toml.j2", "src/{{ project.name }}/logging/config.toml"),
        _ManifestEntry("python_shared.logging.filter.py.j2", "src/{{ project.name }}/logging/filter.py"),
        _ManifestEntry("python_shared.logging.formatter.py.j2", "src/{{ project.name }}/logging/formatter.py"),
        _ManifestEntry("python_shared.logging.logger.py.j2", "src/{{ project.name }}/logging/logger.py"),
        _ManifestEntry("python_shared.docs.index.md.j2", "docs/index.md"),
        _ManifestEntry("python_shared.tests.conftest.py.j2", "tests/conftest.py"),
        _ManifestEntry("python_shared.tests.unit.test_placeholder.py.j2", "tests/unit/test_placeholder.py"),
        _ManifestEntry("python_shared.tests.system.test_build.py.j2", "tests/system/test_build.py"),
    ],
    "python-tool": [
        _ManifestEntry("README.md.j2", "README.md"),
        _ManifestEntry("python_shared.gitignore.j2", ".gitignore"),
        _ManifestEntry("python_shared.Makefile.j2", "Makefile"),
        _ManifestEntry("pyproject.toml.j2", "pyproject.toml"),
        _ManifestEntry("python_tool.__init__.py.j2", "src/{{ project.name }}/__init__.py"),
        _ManifestEntry("python_tool.__main__.py.j2", "src/{{ project.name }}/__main__.py"),
        _ManifestEntry("python_tool.app.py.j2", "src/{{ project.name }}/app/app.py"),
        _ManifestEntry("python_tool.config.py.j2", "src/{{ project.name }}/app/config.py"),
        _ManifestEntry("python_shared.logging.__init__.py.j2", "src/{{ project.name }}/logging/__init__.py"),
        _ManifestEntry("python_shared.logging.config.toml.j2", "src/{{ project.name }}/logging/config.toml"),
        _ManifestEntry("python_shared.logging.filter.py.j2", "src/{{ project.name }}/logging/filter.py"),
        _ManifestEntry("python_shared.logging.formatter.py.j2", "src/{{ project.name }}/logging/formatter.py"),
        _ManifestEntry("python_shared.logging.logger.py.j2", "src/{{ project.name }}/logging/logger.py"),
        _ManifestEntry("python_shared.docs.index.md.j2", "docs/index.md"),
        _ManifestEntry("python_shared.tests.conftest.py.j2", "tests/conftest.py"),
        _ManifestEntry("python_shared.tests.unit.test_placeholder.py.j2", "tests/unit/test_placeholder.py"),
        _ManifestEntry("python_shared.tests.system.test_build.py.j2", "tests/system/test_build.py"),
    ],
    "cpp-library": [
        _ManifestEntry("cpp_shared.README.md.j2", "README.md"),
        _ManifestEntry("cpp_shared.gitignore.j2", ".gitignore"),
        _ManifestEntry("cpp_shared.docs.index.md.j2", "docs/index.md"),
        _ManifestEntry("cpp_library.CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry("cpp_library.src.cpp.j2", "src/{{ project.name }}.cpp"),
        _ManifestEntry("cpp_library.include.h.j2", "include/{{ project.name }}.h"),
        _ManifestEntry("cpp_library.tests.CMakeLists.txt.j2", "tests/CMakeLists.txt"),
        _ManifestEntry("cpp_library.tests.cpp.j2", "tests/test_{{ project.name }}.cpp"),
    ],
    "cpp-tool": [
        _ManifestEntry("cpp_shared.README.md.j2", "README.md"),
        _ManifestEntry("cpp_shared.gitignore.j2", ".gitignore"),
        _ManifestEntry("cpp_shared.docs.index.md.j2", "docs/index.md"),
        _ManifestEntry("cpp_tool.CMakeLists.txt.j2", "CMakeLists.txt"),
        _ManifestEntry("cpp_tool.src.cpp.j2", "src/{{ project.name }}.cpp"),
        _ManifestEntry("cpp_tool.src.main.cpp.j2", "src/main.cpp"),
        _ManifestEntry("cpp_tool.include.h.j2", "include/{{ project.name }}.h"),
        _ManifestEntry("cpp_tool.tests.CMakeLists.txt.j2", "tests/CMakeLists.txt"),
        _ManifestEntry("cpp_tool.tests.cpp.j2", "tests/test_{{ project.name }}.cpp"),
    ],
}


def list_project_types() -> list[str]:
    return list(_MANIFESTS.keys())


def render_project(
    project_type: str,
    name: str,
    output_dir: Path,
    *,
    force: bool = False,
) -> Result[list[Path], InitError]:
    if project_type not in _MANIFESTS:
        return Err(InitError.UnknownType)

    env = Environment(
        loader=FileSystemLoader(str(_DATA_DIR)),
        keep_trailing_newline=True,
    )
    ctx = {"project": {"name": name, "type": project_type}}

    entries = _MANIFESTS[project_type]

    # Resolve all output paths up front so we can check for conflicts before
    # writing anything.
    resolved: list[tuple[_ManifestEntry, Path]] = []
    for entry in entries:
        try:
            out_rel = env.from_string(entry.output).render(ctx)
        except Exception as exc:
            return Err(InitError.RenderFailed)
        out_path = output_dir / out_rel
        resolved.append((entry, out_path))

    if not force:
        for _, out_path in resolved:
            if out_path.exists():
                return Err(InitError.OutputExists)

    written: list[Path] = []
    for entry, out_path in resolved:
        try:
            tmpl = env.get_template(entry.template)
        except TemplateNotFound:
            return Err(InitError.TemplateNotFound)
        try:
            content = tmpl.render(ctx)
        except TemplateSyntaxError:
            return Err(InitError.RenderFailed)

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content)
        written.append(out_path)

    return Ok(written)
