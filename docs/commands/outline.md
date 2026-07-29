# frob outline

Emit a compact structural skeleton of a source file or directory: classes,
functions, signatures, line numbers, and first-sentence docstrings. No bodies.

## Usage

```
frob outline <file-or-dir> [--json] [--all]
```

When given a directory, falls back to `frob map` output for that directory.
`--all` includes private (underscore-prefixed) symbols, hidden by default.

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

Python (tree-sitter-python), C/C++ (tree-sitter-cpp), Rust
(tree-sitter-rust, T-0238). `.strata` design files are also outlined when
frob.lang's grammar for them is available.

## Public API

<!-- frob:describes src/frob/outline/__init__.py::OutlineError -->
<!-- frob:describes src/frob/outline/__init__.py::FunctionOutline -->
<!-- frob:describes src/frob/outline/__init__.py::ClassOutline -->
<!-- frob:describes src/frob/outline/__init__.py::ModuleOutline -->
<!-- frob:describes src/frob/outline/__init__.py::outline_file -->

```python
# frob/outline/__init__.py
class OutlineError(ErrorSet)
    UnsupportedLanguage   # no outline adapter for this file extension
    ParseFailed           # tree-sitter could not parse the file

class FunctionOutline(BaseModel)
    name: str
    signature: str
    line: int
    doc: str = ""

class ClassOutline(BaseModel)
    name: str
    line: int
    methods: list[FunctionOutline]

class ModuleOutline(BaseModel)
    path: str
    lines: int
    imports: list[str]
    functions: list[FunctionOutline]
    classes: list[ClassOutline]
    def as_text(self, include_private: bool = False) -> str
    def as_json(self) -> str

def outline_file(path: Path) -> Result[ModuleOutline, OutlineError]
    # Parses one file and returns its module-level shape; the single entry
    # point behind `frob outline`.
```
