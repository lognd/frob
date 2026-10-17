<!-- mdtest: rule=TICK002 -->
# TICK002 ticket-not-on-base

A directive or trailer names a ticket missing from the base branch.

## What it does

Each ticket id named by a `frob:ticket` directive or trailer of the checked change must exist on the base ref (raised by the `--ticket` scope).

## Why it matters

A reference to a ticket the base branch lacks fails locally and in CI once the ledger commit is not pushed.

## Remedy

Push the ledger commit or fix the id to the full ULID of an existing ticket.

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
