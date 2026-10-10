<!-- mdtest: rule=DSL002 -->
# v1 key forms are read and offered a rewrite

## Rust: note= on a todo

```rust expect=fire
/* frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 note="two words" */ // error: DSL002
fn a() {}
```

## Rust: reason= on an invariant

```rust expect=fire
/* frob:invariant name reason="why" */ // error: DSL002
fn b() {}
```

## Rust: the v2 forms are clean

```rust expect=clean
/* frob:todo 01J9QKX3M8Z4T7N2V5B6C0D1E2 two words */
/* frob:invariant name why */
fn c() {}
```
