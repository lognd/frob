# frob outline

Emit a compact structural skeleton of a source file: classes, functions,
signatures, and line numbers. No bodies.

## Usage

```
frob outline <file> [--json]
```

## Output (default)

```
src/frob/ast/python.py  (195 lines)
  imports: tree_sitter_python, tree_sitter, frob.ast.common
  parse_file(path: Path) -> tuple[bytes, Tree]  [L18]
  parse_bytes(src: bytes) -> tuple[bytes, Tree]  [L23]
  get_imports(mod_tag: ModuleTag, root: Path) -> list[ModuleTag]  [L32]
  class MyClass  [L80]
    process(self, data: bytes) -> list  [L81]
    _private(self) -> None  [L85]
```

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
    {"name": "parse_file", "signature": "parse_file(path: Path) -> tuple[bytes, Tree]", "line": 18}
  ],
  "classes": [
    {
      "name": "MyClass",
      "line": 80,
      "methods": [
        {"name": "process", "signature": "process(self, data: bytes) -> list", "line": 81}
      ]
    }
  ]
}
```

## Language support

Python (tree-sitter-python), C/C++ (tree-sitter-cpp).
