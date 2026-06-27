# frob scaffold

Scaffold new projects from registered templates. (`frob init` is a deprecated alias.)

## Usage

```bash
frob scaffold list                      # list available project types
frob scaffold new python-library mylib  # scaffold into ./mylib/
frob scaffold new python-library mylib --output /path/to/parent/
frob scaffold new cpp-cmake myproject --force  # overwrite existing files
```

## Project types

| Type | Contents |
|------|---------|
| `python-library` | `pyproject.toml`, `src/<name>/`, `tests/`, `Makefile`, `.gitignore` |
| `python-cli` | Above + `__main__.py` entry point |
| `cpp-cmake` | `CMakeLists.txt`, `src/`, `include/`, `tests/` (Catch2), `Makefile` |

Run `frob scaffold list` to see the current registry.

## Template layout

Templates live under `src/frob/scaffold/data/`:

```
scaffold/data/
  shared/
    python/          -- shared across all Python types
      Makefile.j2
      .gitignore.j2
      pyproject.toml.j2
    cpp/             -- shared across all C++ types
      Makefile.j2
  types/
    python-library/
      __init__.py.j2
      ...
    cpp-cmake/
      CMakeLists.txt.j2
      ...
```

Jinja2 variables available in all templates:

| Variable | Value |
|---------|-------|
| `name` | Project name as passed on the CLI |
| `package` | `name` with hyphens replaced by underscores |

## Adding a project type

1. Create `src/frob/scaffold/data/types/<type-name>/` with `.j2` templates.
2. Add an entry to `_MANIFESTS` in `src/frob/scaffold/project.py`.
3. Add a `frob scaffold list` entry string in the same file.
4. Include the new path in `[tool.setuptools.package-data]` in `pyproject.toml`
   if the type contains non-Python files.
