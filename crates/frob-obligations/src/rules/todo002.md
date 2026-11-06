<!-- mdtest: rule=TODO002 -->
# TODO002 todo-ticket-terminal

A `frob:todo` directive points at a ticket that is already done or dropped.

## What it does

The ticket named by the directive is in the terminal category, so the work it owned is finished (or abandoned) yet the marker remains. The finding is located on the directive. When the ledger holds no ticket to resolve the directive against, the rule examined nothing and says so as an unresolved finding.

## Why it matters

A marker that outlives its ticket claims work is pending that nobody owns.

## Remedy

Do the work, remove the marker, or re-point it at a live ticket.

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
