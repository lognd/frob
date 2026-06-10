# frob bundle

Assemble the minimal context needed to implement or review a specific function,
formatted for direct use as a subagent prompt.

## Usage

```
frob bundle <file> <target> [--depth N] [--format text|json|markdown]
```

`<target>` is a dotted name: `function_name` or `ClassName.method`.
`--depth` controls how many levels of local imports to inline (default: 1).

## What it produces

1. The **focus file**, stubbed so only `<target>` has its full body.
2. For each **local import** of that file (up to `--depth` levels): all
   function/method signatures with no bodies.
3. An **estimated token count** so you can budget subagent context.

## Example

```
frob bundle src/frob/stub/__init__.py stub_file
```

Output (markdown format):

```markdown
# Bundle: stub_file  |  src/frob/stub/__init__.py
# Estimated tokens: ~420

## src/frob/stub/__init__.py  [FOCUS]
```python
from frob.ast import python as _py
...

def stub_file(path: Path, target: str) -> Result[str, StubError]:
    ext = path.suffix.lower()
    if ext in _PY_EXTS:
        ...  # full body here
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

# 5. Apply the subagent's patch
frob patch /tmp/stub_patch.diff
```
