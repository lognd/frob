# frob exports

Generate a ready-to-paste `__init__.py` from all public symbols in a package
directory. Also used by `frob check` to detect missing exports.

## Usage

```bash
frob exports src/frob/edit/                      # show generated __init__.py
frob exports src/frob/edit/ --all                # include private symbols (_foo)
frob exports src/frob/ --exclude mission --exclude dispatch
frob exports src/frob/edit/ --write              # write __init__.py in place
frob exports src/frob/edit/ --json
```

## Output

```python
from frob.edit._impl import IsolatedSymbol, StagedPatch, CommitResult
from frob.edit._impl import isolate, stage, commit, status, replace

__all__ = [
    "CommitResult",
    "IsolatedSymbol",
    "StagedPatch",
    "commit",
    "isolate",
    "replace",
    "stage",
    "status",
]
```

### Duplicate symbol handling

When two modules in the same package export the same name (e.g. both
`stub_runner` and `exports_runner` export `run`), the conflicting names are
aliased automatically:

```python
from frob.app.stub_runner import run as stub_runner_run
from frob.app.exports_runner import run as exports_runner_run

__all__ = ["exports_runner_run", "stub_runner_run"]
```

## Integration with frob check

`frob check src/` runs `frob exports` on every package and compares the output
against the existing `__init__.py`. Any public symbol that is defined but not
exported is reported as a warning.

## Flags

| Flag | Description |
|------|-------------|
| `--all` | Include private symbols (names starting with `_`) |
| `--exclude MODULE` | Skip a submodule entirely (repeatable) |
| `--write` | Write the generated `__init__.py` directly to the package directory |
| `--json` | Output structured `ExportsResult` as JSON |

## Public API

<!-- frob:describes src/frob/exports/__init__.py::ExportsError -->
<!-- frob:describes src/frob/exports/__init__.py::ModuleExports -->
<!-- frob:describes src/frob/exports/__init__.py::ExportsResult -->
<!-- frob:describes src/frob/exports/__init__.py::exports_package -->

```python
# frob/exports/__init__.py
class ExportsError(ErrorSet)
    NotADirectory   # path is not a directory
    NoSourceFiles   # no Python source files found in directory

class ModuleExports(BaseModel)
    module: str
    symbols: list[str]

class ExportsResult(BaseModel)
    package_dir: str
    modules: list[ModuleExports]
    def as_text(self) -> str    # a generated __init__.py, duplicate names aliased
    def as_json(self) -> str

def exports_package(
    pkg_dir: Path, *, include_private: bool = False,
    exclude_modules: list[str] | None = None,
) -> Result[ExportsResult, ExportsError]
    # Walks pkg_dir's modules via frob.outline, collects public symbols per
    # module; the single entry point behind `frob exports`.
```
