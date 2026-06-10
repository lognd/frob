# frob stub

Reduce a source file to the item of interest, stubbing out everything else.

## Usage

```
frob stub <file> <target> [--output <file>]
```

`<target>` is a dotted name: `ClassName`, `function_name`, or `ClassName.method`.

Output goes to stdout unless `--output` is given.

## What it produces

Given a file with multiple classes and functions, `frob stub` keeps `<target>`
intact and replaces every other function/method body with `...` (Python) or a
forward declaration (C++), while preserving all signatures and type annotations.

### Python example

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
