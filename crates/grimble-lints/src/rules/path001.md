<!-- mdtest: rule=PATH001 -->
# PATH001 absolute-host-path

A string literal that is an absolute host path.

## What it does

Fires for a string literal in Rust, Python, TypeScript or C# that is an absolute path of one machine: `/home/<name>/`, `/Users/<name>/`, `/root/`, a `/tmp/...` path, a drive path (`X:\` or `X:/`) or a UNC path. A lone `/`, a URL, a shebang line and the entries of `[path] allowed` (default `/dev/null`) are not host paths. In test code and fixture files the finding is Advisory, elsewhere it is an Error.

## Why it matters

A path that names one machine compiles everywhere and is wrong on every other platform; it broke CI on the first Windows run.

## Remedy

Build the path from a root the caller passes in (`Path::join`), or from a temporary directory the test creates, instead of writing the absolute path.

## Examples

### Fires case 1

```rust expect=fire file=src/lib.rs
fn fixture() -> &'static str {
    "D:\\a\\frob\\frob\\fixture.txt"
}
```

### Clean case 2

```rust expect=clean file=src/lib.rs
fn fixture(root: &std::path::Path) -> std::path::PathBuf {
    root.join("fixture.txt")
}
```
