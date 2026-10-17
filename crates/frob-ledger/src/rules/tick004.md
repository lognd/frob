<!-- mdtest: rule=TICK004 -->
# TICK004 absolute-home-path

A ledger file holds `/home/<name>/`, `/Users/<name>/`, `/root/` or `C:\Users\<name>\`.

## What it does

Scans the committed ledger files for absolute home directory paths.

## Why it matters

Such a path publishes the local user name and directory layout of everyone who pushes.

## Remedy

`frob ticket doctor --fix` scrubs the paths in one new commit (history is never rewritten); a hand edit to `~/` or a path relative to the repository parent clears the finding too.

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
