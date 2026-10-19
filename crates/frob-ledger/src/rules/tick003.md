<!-- mdtest: rule=TICK003 -->
# TICK003 dangling-link

A ticket link or parent points at a missing ticket.

## What it does

Every link and parent of a ticket must name a ticket that exists in the ledger.

## Why it matters

A dangling link breaks dependency and blocker queries that walk the graph.

## Remedy

Remove the link with `frob ticket unlink`, or restore the ticket.

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
