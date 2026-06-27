# frob exports

Generate a ready-to-paste `__init__.py` from all public symbols in a package
directory. Also used by `frob check` to detect missing exports.

## Usage

```bash
frob exports src/frob/edit/         # show generated __init__.py
frob exports src/frob/edit/ --all   # include private symbols (_foo)
frob exports src/frob/ --exclude mission --exclude dispatch
frob exports src/frob/edit/ --json
```

## Output

```python
from frob.edit._impl import IsolatedSymbol, StagedPatch, CommitResult
from frob.edit._impl import isolate, stage, commit, status, replace

__all__ = [
    "IsolatedSymbol",
    "StagedPatch",
    "CommitResult",
    "isolate",
    "stage",
    "commit",
    "status",
    "replace",
]
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
| `--json` | Output structured `ExportsResult` as JSON |
