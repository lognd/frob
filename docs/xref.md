# frob xref

Find where a symbol is defined and every file that references it.

## Usage

```
frob xref <symbol> [path] [--lang python|cpp] [--json]
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

## Why it exists

Before changing a function signature or moving a module, Claude needs to know
the blast radius. Without `xref`, that means grepping and reading every hit.
`xref` returns a compact list: definition site + every call site with one line
of context, ready for impact analysis.

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
