<!-- mdtest: rule=TICK001 -->
# TICK001 frontmatter-differs-from-fold

A ticket's `ticket.md` disagrees with the fold of its events.

## What it does

`ticket.md` is a cache of the events; when it disagrees (a hosting provider's merge button skipped the merge driver, or a hand edit) the events win.

## Why it matters

A stale frontmatter shows tickets in a state their history does not support.

## Remedy

Run `frob ticket doctor --fix` to rewrite the frontmatter from the events.

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
