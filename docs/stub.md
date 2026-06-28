# frob stub

Reduce a source file to the item(s) of interest, stubbing out everything else.

## Usage

```
frob stub <file> <target> [<target>...] [--output <file>]
```

`<target>` is a dotted name: `ClassName`, `function_name`, or `ClassName.method`.
Multiple targets may be given; all listed targets keep their full bodies.

Output goes to stdout unless `--output` is given.

## What it produces

Given a file with multiple classes and functions, `frob stub` keeps each
`<target>` intact and replaces every other function/method body with `...`
(Python) or a forward declaration (C++), while preserving all signatures and
type annotations.

### Python example -- single target

```
frob stub src/mymodule.py MyClass.process
```

Input:
```python
import os
from pathlib import Path

def helper(x: int) -> str: ...   # <-- real body stripped to ...

class MyClass:
    def process(self, data: bytes) -> list[str]:
        # kept verbatim
        return data.decode().splitlines()

    def _private(self) -> None:   # <-- body stubbed
        ...
```

### Python example -- multiple targets

```
frob stub src/mymodule.py helper MyClass.process
```

Both `helper` and `MyClass.process` keep their full bodies; `_private` and any
other functions are stubbed.

### C++ example

```
frob stub src/engine.cpp Engine::run
```

Non-target function definitions are reduced to declarations; the target
definition is kept verbatim.

## Language support

| Language | Stub strategy |
|----------|--------------|
| Python | tree-sitter-python parse, body replacement via source slicing |
| C/C++ | tree-sitter-cpp parse, body replacement with `;` |

## Error handling

Returns `Result[str, StubError]`:

- `StubError.ParseFailed` -- tree-sitter could not parse the file
- `StubError.TargetNotFound` -- `<target>` not found in the parsed tree
- `StubError.UnsupportedLanguage` -- no adapter for this file extension
