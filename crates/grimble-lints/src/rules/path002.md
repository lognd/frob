<!-- mdtest: rule=PATH002 -->
# PATH002 string-path-separator

A path turned into a string and then handled with a literal separator.

## What it does

Fires when a value produced by turning a path into a string (Rust `to_str`, `to_string_lossy`, `display`, `as_os_str`; Python `str(p)`, `os.fspath`) is split, joined, concatenated, compared, trimmed or searched with a literal `/` or `\` in the same function. A language whose adapter has no path-conversion roles is Unresolved, never clean. A repository-relative path type that stores forward slashes by contract does not fire.

## Why it matters

`/` and `\` differ between hosts, so the comparison is right on one platform and silently wrong on the other.

## Remedy

Use `Path::join`, `components`, `strip_prefix` and `Path` equality, or the repository-relative path type for paths stored in data.

## Examples

### Fires case 1

```rust expect=fire file=src/lib.rs
use std::path::Path;

fn allowed(p: &Path) -> bool {
    let s = p.to_string_lossy();
    s.starts_with("src/")
}
```

### Clean case 2

```rust expect=clean file=src/lib.rs
use std::path::Path;

fn allowed(p: &Path) -> bool {
    p.starts_with("src")
}
```

### Unresolved case 3

```typescript expect=unresolved file=src/a.ts
export function allowed(p: string): boolean {
  return p.startsWith("src/");
}
```
