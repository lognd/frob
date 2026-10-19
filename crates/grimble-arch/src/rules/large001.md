<!-- mdtest: rule=LARGE001 -->
# LARGE001 arch-large-unit

A function, method or type longer than the configured line limit.

## What it does

Fires for every function, method, struct, enum, trait, class, interface or record whose source spans more than `large_lines` lines (default 400). A length is exact, so the rule is never Unresolved. `large_lines = 0` turns the rule off.

## Why it matters

A unit that long is several units; it resists review and attracts unrelated change.

## Remedy

Split the unit, or raise `large_lines` for the repo.

## Examples

### Fires case 1

```rust expect=fire file=src/lib.rs config="small"
pub fn long() {
    let a = 1;
    let b = 2;
    let c = 3;
}
```

### Clean case 2

```rust expect=clean file=src/lib.rs config="big"
pub fn short() {
    let a = 1;
}
```
