<!-- mdtest: rule=SCOPE001 -->
# SCOPE001 path outside the lease

The ticket under test is scoped to `src/a/**`; the block is a new file.

## A new file outside the scope fires

```rust expect=fire file=src/b/lib.rs
//! Outside.
```

## A new file inside the scope is clean

```rust expect=clean file=src/a/lib.rs
//! Inside.
```
