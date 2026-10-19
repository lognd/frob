<!-- mdtest: rule=DRIFT003 -->
# DRIFT003 stale-ack

A symbol was acked, its signature changed, and no `frob:doc` directive covers it.

## What it does

Fires when a lock entry records an older signature of a symbol and no `frob:doc` directive ties the symbol to documentation.

## Why it matters

The ack recorded an older contract and nothing tells anybody to re-read anything.

## Remedy

Re-ack the symbol, or bind it to the doc that describes it.

## Examples

### A drifted case fires

```rust expect=fire file=src/lib.rs
pub fn bound() {}
```

### An unchanged case is clean

```rust expect=clean file=src/lib.rs
pub fn unbound() {}
```
