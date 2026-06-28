# frob bundle

Assemble the minimal context needed to implement or review a specific function,
formatted for direct use as a subagent prompt.

## Usage

```
frob bundle <file> <target> [--depth N] [--format text|json|markdown]
```

`<target>` is a dotted name: `function_name` or `ClassName.method`.
`--depth` controls how many levels of local imports to inline (default: 1).

Token count is written to stderr so it does not pollute the markdown output.

## What it produces

1. The **focus file** -- module-level imports + the full body of `<target>` only.
   Sibling functions are not included.
2. Any private helpers called by `<target>` that are defined in the same file,
   appended as one-liner stubs under `# same-file helpers called by target:`.
3. For each **local import** of that file (up to `--depth` levels): all
   function/method signatures with no bodies (role=SIGNATURES).

## Example

```
frob bundle src/frob/stub/__init__.py stub_file
```

Token estimate printed to stderr: `# ~420 tokens`

Output (markdown format):

```markdown
# Bundle: `stub_file`

## src/frob/stub/__init__.py  [FOCUS]
```python
from pathlib import Path
from typani import Err, Ok
from typani.result import Result
from frob.ast import python as _py

def stub_file(path: Path, target: str) -> Result[str, StubError]:
    ext = path.suffix.lower()
    if ext in _PY_EXTS:
        return _py_stub(path, target)
    return Err(StubError.UnsupportedLanguage)

# same-file helpers called by target:
def _py_stub(path: Path, target: str) -> Result[str, StubError]: ...
```

## frob.ast.python  [SIGNATURES]
```python
def parse_file(path: Path) -> tuple[bytes, Tree]: ...
def parse_bytes(src: bytes) -> tuple[bytes, Tree]: ...
def emit_stub(source: bytes, tree: Tree, target: str) -> str: ...
```
```

## Why it exists

Dispatching a Haiku subagent to implement a function works best when the agent
receives exactly the context it needs -- no more, no less. Without `bundle`,
Claude must manually stub files, collect signatures, and format a prompt.
`bundle` does all of that in one call.

## Typical agentic workflow

```
# 1. Get project map
frob map src/

# 2. See what a target file contains
frob outline src/frob/stub/__init__.py

# 3. See what uses stub_file (impact analysis)
frob xref stub_file src/

# 4. Assemble context for a subagent tasked with rewriting stub_file
frob bundle src/frob/stub/__init__.py stub_file > /tmp/context.md
# ... paste into subagent prompt ...

# 5. Apply the subagent's output
frob edit src/frob/stub/__init__.py stub_file --stage
frob edit src/frob/stub/__init__.py --commit
```
