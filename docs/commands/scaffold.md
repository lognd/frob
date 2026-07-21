# frob scaffold

Scaffold new projects from registered templates. Every type targets
ABSOLUTELY MINIMAL boilerplate: `frob scaffold new <type> demo && cd demo
&& git init && make check` should go green immediately, with no manual
fixups, for the Python and Rust types (the web-app type needs `npm`
available; verify by inspection if it isn't).

## Usage

<!-- frob:describes src/frob/__main__.py::_add_scaffold_parser -->
```bash
frob scaffold list                  # list available project types
frob scaffold new python-tool demo  # scaffold into ./demo/
frob scaffold new python-tool demo --output /path/to/parent/
frob scaffold new pyo3-library demo --force  # overwrite existing files
```

## Project types

| Type | Stack | Contents |
|------|-------|---------|
| `python-tool` | uv + setuptools | `pyproject.toml` (typani+pydantic, dev group), `src/<name>/` with the App/AppConfig/`__main__` pattern, house logging setup, `frob.toml` (strict gates), `tickets/`, `invariants/`, `.env.example`, `Makefile` (`install/format/lint/typecheck/test/coverage/check`), CI + release workflows |
| `python-library` | uv + setuptools | Same base as `python-tool` minus the CLI entry point/App layer |
| `pyo3-library` | uv + maturin + cargo workspace | `crates/` (Rust, pyo3 extension) + `python/<name>/` layout (lithos-style), `rust-toolchain.toml`, `frob.toml` with both `python` and `rust` test runners, Makefile wiring `cargo fmt`/`clippy` into `check`, CI + release workflows |
| `web-app` | Vite + React + TypeScript + Vitest | `src/`, `tests/unit/`, ESLint 9 flat config, Prettier, `frob.toml` (`typescript` test runner), CI |
| `cpp-library` / `cpp-tool` | CMake + ctest | `src/`, `include/`, `tests/`, `frob.toml` (`cpp` test runner via ctest), CI + release + branch-protection workflows |
| `pybind11-library` | CMake + scikit-build + pytest | `src/`, bindings, `tests/`, `frob.toml` (`python` test runner), CI |

Run `frob scaffold list` to see the current registry.

## CI/CD design (every type)

`.github/workflows/ci.yml`: push+PR trigger, `concurrency.cancel-in-progress`,
one `check` job per stack running lint -> typecheck -> test(+coverage) ->
`frob check`. The `frob check` step is guarded: it installs frob via
`uv tool install frob`, then only runs it if `frob graph --help` actually
works, emitting a `::notice::` and skipping otherwise. This exists because
frob is not yet published to PyPI (pre-0.1.0) -- `uv tool install frob`
would otherwise install nothing or something stale, and a naive
`frob check` step would red-herring CI with an unrelated failure. Once
frob 0.1.0 ships, this starts enforcing automatically with no workflow
edit required.

`python-tool` and `pyo3-library` additionally get `.github/workflows/release.yml`:
triggered on `v*` tags, builds via `uv build` / `maturin build --release`,
and publishes to PyPI through `pypa/gh-action-pypi-publish` using OIDC
trusted publishing (no stored API token). The workflow's header comment
documents the one-time PyPI "Publishing" trusted-publisher setup.

## Template layout

Templates live under `src/frob/scaffold/data/`:

```
scaffold/data/
  shared/
    python/          -- shared across all Python types (Makefile, gitignore,
                         pyproject.toml, logging/, frob.toml, tests/, github/)
    cpp/             -- shared across all C++ types (Makefile, gitignore,
                         frob.toml, docs/, github/)
    pyo3/            -- gitignore shared by pyo3-library
    pybind11/        -- gitignore shared by pybind11-library
  types/
    python-tool/
      app/, docs/, tests/, github/, frob.toml.j2, ...
    python-library/
      __init__.py.j2
    pyo3-library/
      crates/, python/, tests/, github/, Cargo.toml.j2, frob.toml.j2, ...
    web-app/
      src/, tests/, github/, package.json.j2, ...
    cpp-library/ cpp-tool/ pybind11-library/
      ...
```

Jinja2 variables available in all templates:

| Variable | Value |
|---------|-------|
| `project.name` | Project name as passed on the CLI |
| `project.type` | The scaffold type being rendered (e.g. `"python-tool"`) -- used by `shared/python/pyproject.toml.j2` to gate the CLI entry point to `python-tool` only |

## Public API

<!-- frob:describes src/frob/scaffold/project.py::ScaffoldError -->
<!-- frob:describes src/frob/scaffold/project.py::list_project_types -->
<!-- frob:describes src/frob/scaffold/project.py::render_project -->
<!-- frob:describes src/frob/scaffold/project.py::install_worktree_lease_hook -->

```python
# frob/scaffold/project.py
class ScaffoldError(ErrorSet)
    # Failure values: unknown type, missing template, existing output
    # files without --force, a Jinja2 render error, or (T-0431) a hook
    # install failure (not a git repo, or the write itself failed).

def list_project_types() -> list[str]
    # The registered scaffold type names, read directly off _MANIFESTS.

def render_project(project_type, name, output_dir, *, force=False) -> Result[list[Path], ScaffoldError]
    # Render one registered type's templates into output_dir; the single
    # entry point behind `frob scaffold new`.

def install_worktree_lease_hook(root, *, force=False) -> Result[tuple[Path, ...], ScaffoldError]
    # T-0431: installs pre-commit + pre-merge-commit git hooks into root's
    # real hooks directory (git rev-parse --git-path hooks) that abort
    # loudly whenever FROB_AGENT is set non-empty -- catches a stray raw
    # `git commit`/`git merge` an agent shell ran directly against the
    # wrong checkout, independent of frob.tickets' own worktree-lease
    # guard (docs/modules/tickets.md#worktree-lease-guard-t-0431). Refuses
    # to overwrite an existing hook file without force=True.
```

## Adding a project type

1. Create `src/frob/scaffold/data/types/<type-name>/` with `.j2` templates.
2. Add a `_MANIFESTS["<type-name>"]` entry in `src/frob/scaffold/project.py`
   (`list_project_types()` reads the registry directly -- no separate list
   to keep in sync).
3. Include the new path glob in `[tool.setuptools.package-data]` in
   `pyproject.toml` if the type introduces a new file extension.
4. Verify the DX bar: render the type into a temp dir, `git init`, and run
   its `make check` (or stack-equivalent) end to end -- see
   `tests/system/test_scaffold_dx.py` for the pattern.
