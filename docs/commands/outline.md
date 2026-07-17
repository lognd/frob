# frob outline

Emit a compact structural skeleton of a source file or directory: classes,
functions, signatures, line numbers, and first-sentence docstrings. No bodies.

## Usage

```
frob outline <file-or-dir> [--json]
```

When given a directory, falls back to `frob map` output for that directory.

## Output (default)

```
src/frob/ast/python.py  (195 lines)
  imports: tree_sitter_python, tree_sitter, frob.ast.common
  parse_file(path: Path) -> tuple[bytes, Tree]  [L18] -- Parse a .py file and return raw bytes + tree.
  parse_bytes(src: bytes) -> tuple[bytes, Tree]  [L23]
  get_imports(mod_tag: ModuleTag, root: Path) -> list[ModuleTag]  [L32] -- Collect local imports from a module.
  class MyClass  [L80]
    process(self, data: bytes) -> list  [L81]
    _private(self) -> None  [L85]
```

The `-- <text>` suffix shows the first sentence of the function's docstring,
when one is present. Functions with no docstring show no suffix.

## Why it exists

Reading a whole file costs tokens. `outline` answers "what is in this file and
where?" in roughly 1/10th the tokens, letting Claude decide whether to read the
whole file, stub it, or skip it entirely.

## JSON output (`--json`)

```json
{
  "path": "src/frob/ast/python.py",
  "lines": 195,
  "imports": ["tree_sitter_python", "tree_sitter", "frob.ast.common"],
  "functions": [
    {"name": "parse_file", "signature": "parse_file(path: Path) -> tuple[bytes, Tree]", "line": 18, "doc": "Parse a .py file and return raw bytes + tree."}
  ],
  "classes": [
    {
      "name": "MyClass",
      "line": 80,
      "methods": [
        {"name": "process", "signature": "process(self, data: bytes) -> list", "line": 81, "doc": ""}
      ]
    }
  ]
}
```

## Language support

Python (tree-sitter-python), C/C++ (tree-sitter-cpp).
