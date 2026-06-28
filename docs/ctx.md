# frob ctx

Adaptive context gatherer. Automatically selects the right depth of context
for a given symbol -- stub, bundle, or full -- based on function complexity.

## Usage

```bash
frob ctx src/file.py MyFunction
frob ctx src/file.py MyClass.method --root src/
frob ctx src/file.py MyFunction --depth 2
frob ctx src/file.py MyFunction --json
```

**Use `frob ctx` instead of manually choosing between `frob stub`, `frob bundle`,
and reading the full file.** It checks complexity and picks the minimum context
needed to understand the symbol.

## Tier selection

| Condition | Tier | What you get |
|-----------|------|-------------|
| < 12 lines AND <= 2 import deps | `stub` | Function signature + one-liner stubs for neighbors |
| < 40 lines AND <= 4 import deps AND few callers | `bundle` | Function + stubbed import signatures |
| >= 40 lines OR > 4 import deps OR many xref callers | `full` | Bundle + xref caller list + docstrings |

The tier and estimated token count are shown in the output header:

```
# frob ctx: MyFunction  [tier=bundle  ~342 tok]
# reason: 23 lines
...
```

## Flags

| Flag | Description |
|------|-------------|
| `--root DIR` | Project root for xref search (default: file's parent) |
| `--depth N` | Bundle import depth (default: 1) |
| `--json` | Output structured `CtxResult` as JSON |

## JSON output

```json
{
  "path": "src/frob/module/__init__.py",
  "symbol": "MyFunction",
  "tier": "bundle",
  "tier_reason": "23 lines",
  "content": "..."
}
```

## When to override

If `frob ctx` picks `stub` but you know the function has subtle dependencies:
use `frob bundle` directly with `--depth 2`.

If `frob ctx` picks `full` for a large function but you only need to see its
callers: use `frob xref` directly.

## Token cost reference

| Tier | Typical tokens |
|------|---------------|
| stub | 20-80 |
| bundle | 200-600 |
| full | 400-1200 |
