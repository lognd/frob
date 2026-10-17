<!-- mdtest: rule=SCOPE001 -->
# SCOPE001 path-outside-lease

A changed path lies outside the globs of the ticket's scope lease.

## What it does

Every path of the diff against the base must match a glob of the ticket's scope lease. Paths matching `[lease] shared_files` are exempt, and so is the ticket's own changelog fragment (`changelog.d/<its ULID>.<type>.md`); other tickets' fragments are not.

## Why it matters

A change outside the lease collides with whoever holds the neighbouring paths.

## Remedy

Widen the ticket's scope (`frob ticket update`) and re-acquire the lease, or move the change to a ticket that owns the path.

## Examples

### A violating case fires

```rust expect=fire file=src/lib.rs
pub fn placeholder() {}
```

### A conforming case is clean

```rust expect=clean file=src/lib.rs
pub fn placeholder() {}
```
