# frob xref

Find where a symbol is defined and every file that references it.

## Usage

```
frob xref <symbol> [path] [--lang python|cpp] [--cross-file] [--json]
```

`path` defaults to the current directory. `<symbol>` can be a function name,
class name, or method name (bare, not dotted).

## Output (default)

```
stub_file
  defined:  src/frob/stub/__init__.py:28
  used by:
    src/frob/app/stub_runner.py:17      result = stub_file(cfg.stub_file, ...)
    tests/test_stub.py:23               result = stub_file(py_file, "MyClass.process")
    tests/test_stub.py:29               result = stub_file(py_file, "helper")
```

## Cross-file relationships (`--cross-file`)

`--cross-file` additionally shows which other files the defining file calls into,
giving a two-directional picture of dependencies (callers above, callees below).

```
stub_file
  defined:  src/frob/stub/__init__.py:28
  used by:
    src/frob/app/stub_runner.py:17
  calls into:
    src/frob/ast/python.py
    src/frob/ast/cpp.py
```

## Why it exists

Before changing a function signature or moving a module, Claude needs to know
the blast radius. Without `xref`, that means grepping and reading every hit.
`xref` returns a compact list: definition site + every call site with one line
of context, ready for impact analysis.

## Flags

| Flag | Description |
|------|-------------|
| `--lang` | Force language (python or cpp); auto-detected by default |
| `--cross-file` | Also show files that the defining file calls into |
| `--json` | Output structured `XrefResult` as JSON |

## JSON output (`--json`)

```json
{
  "symbol": "stub_file",
  "definition": {"file": "src/frob/stub/__init__.py", "line": 28},
  "usages": [
    {"file": "src/frob/app/stub_runner.py", "line": 17, "context": "result = stub_file(cfg.stub_file, cfg.stub_target)"},
    {"file": "tests/test_stub.py", "line": 23, "context": "result = stub_file(py_file, \"MyClass.process\")"}
  ]
}
```

## Language support

Python (tree-sitter identifier search), C/C++ (tree-sitter identifier search).
Plain text grep fallback for unknown extensions.

## Public API

<!-- frob:describes src/frob/xref/__init__.py::XrefError -->
<!-- frob:describes src/frob/xref/__init__.py::Definition -->
<!-- frob:describes src/frob/xref/__init__.py::Usage -->
<!-- frob:describes src/frob/xref/__init__.py::XrefResult -->
<!-- frob:describes src/frob/xref/__init__.py::xref -->

```python
# frob/xref/__init__.py
class XrefError(ErrorSet)
    NoFilesFound   # no source files found under the given path

class Definition(BaseModel)
    file: str
    line: int

class Usage(BaseModel)
    file: str
    line: int
    context: str

class XrefResult(BaseModel)
    symbol: str
    definition: Definition | None
    usages: list[Usage]
    def as_text(self, cross_file: bool = False) -> str
    def as_json(self) -> str

def xref(symbol: str, root: Path, lang: str | None = None) -> Result[XrefResult, XrefError]
    # Collects source files, finds symbol's definition and every usage; the
    # single entry point behind `frob xref`.
```
