<!-- mdtest: rule=TEST001 -->
# TEST001 tests target missing

A `frob:tests` directive must name something the graph can find.

## A directive naming no test fires

```text expect=fire
=== src/lib.rs
//! Library.

/* frob:tests tests::missing */
/// Bound to nothing.
pub fn dangling() {}
```

## A directive naming a test function is clean

```text expect=clean
=== src/lib.rs
//! Library.

/* frob:tests adds_one */
/// Adds one.
pub fn add_one(x: u32) -> u32 {
    x + 1
}

#[test]
fn adds_one() {
    assert_eq!(add_one(1), 2);
}
```
