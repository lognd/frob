<!-- mdtest: rule=AFFECT001 -->
# AFFECT001 dependents of a changed public contract

The baseline acknowledges `base`, which `caller` uses. Each block is the
`src/lib.rs` that replaces it.

## A changed signature with unacknowledged dependents fires

```rust expect=fire file=src/lib.rs
pub fn base(x: u64) -> u32 {
    (x * 2) as u32
}

pub fn caller(x: u32) -> u32 {
    base(u64::from(x)) + 1
}
```

## An unchanged signature is clean

```rust expect=clean file=src/lib.rs
pub fn base(x: u32) -> u32 {
    x * 2
}

pub fn caller(x: u32) -> u32 {
    base(x) + 1
}
```
