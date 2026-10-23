<!-- mdtest: rule=DRIFT002 -->
# DRIFT002 dangling-doc-target

A `frob:doc` directive names a markdown section that does not exist.

## What it does

Fires when the file or heading a `frob:doc` directive points at cannot be found. The message carries the nearest heading slug of the target file by edit distance.

## Why it matters

A binding to nothing guards nothing: the symbol looks documented while no doc is tied to it.

## Remedy

Fix the path or the slug in the directive, or restore the heading. When `docs/MOVED.toml` lists the old anchor, the message names its new location; `frob doc remap` rewrites every such reference.

## Examples

### A drifted case fires

```rust expect=fire file=src/lib.rs
pub fn bound() {}
```

### An unchanged case is clean

```rust expect=clean file=src/lib.rs
pub fn unbound() {}
```
