# frob exports

Generate a ready-to-paste `__init__.py` from all public symbols in a package
directory. Also used by `frob check` to detect missing exports. Also
available as `frob design exports` (T-1568) -- same flags, same code.

## Usage

<!-- frob:describes src/frob/_cli_parsers/_core.py::_add_exports_parser -->
```bash
frob exports src/frob/edit/                      # show generated __init__.py
frob exports src/frob/edit/ --all                # include private symbols (_foo)
frob exports src/frob/ --exclude mission --exclude dispatch
frob exports src/frob/edit/ --write              # write __init__.py in place
frob exports src/frob/edit/ --json
frob exports src/frob/ --consumers exports_package  # who imports this symbol
frob exports src/frob/ --consumers exports_package --lang python --json
```

## Output

<!-- frob:waive DOC004 reason="illustrative generated-__init__.py OUTPUT SHAPE only -- frob.edit._impl is a stale example module (the frob edit command was removed) but the block demonstrates frob exports' output format, not a real, currently-importable module; T-0436" -->

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

<!-- frob:waive DOC004 reason="illustrative duplicate-symbol-aliasing example -- frob.app.stub_runner/exports_runner are stand-in module names for the mechanism being explained, not real modules; T-0436" -->

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
| `--json` | Output structured `ExportsResult` as JSON (or `ConsumersResult` with `--consumers`) |
| `--consumers SYMBOL` | Look up who imports `SYMBOL` under `<path>` instead of listing package exports (`frob.exports.exports_consumers`, T-0858/T-0876) |
| `--lang {python,cpp,c}` | Language override for `--consumers` (default: auto-detect) |

## Public API

<!-- frob:describes src/frob/exports/__init__.py::ExportsError -->
<!-- frob:describes src/frob/exports/__init__.py::ModuleExports -->
<!-- frob:describes src/frob/exports/__init__.py::ExportsResult -->
<!-- frob:describes src/frob/exports/__init__.py::exports_package -->
<!-- frob:describes src/frob/exports/__init__.py::ConsumersResult -->
<!-- frob:describes src/frob/exports/__init__.py::exports_consumers -->

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

class ConsumersResult(BaseModel)
    symbol: str
    consumers: list[ConsumerRef]
    def as_text(self) -> str    # "symbol" + "imported by: file:line context" per consumer
    def as_json(self) -> str

def exports_consumers(
    symbol: str, root: Path, *, lang: str | None = None,
) -> Result[ConsumersResult, ExportsError]
    # Which files actually import `symbol` under `root` (narrowed from
    # frob.xref's raw usages to real import statements); the library entry
    # point behind `frob exports --consumers` (T-0876).
```
