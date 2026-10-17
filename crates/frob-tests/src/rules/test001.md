<!-- mdtest: rule=TEST001 -->
# TEST001 tests-target-missing

A `frob:tests` directive must name something the symbol graph can find.

## What it does

On a non-test item the target names a test and must resolve to a test function; inside a test item the target is the symbol the test covers and must resolve to any symbol. A target that resolves to nothing is flagged at the directive.

## Why it matters

A coverage claim that points at nothing is silent: the symbol looks covered while no test is bound to it.

## Remedy

Fix the symref, or remove the directive.

## Examples

### A target that names no test fires

```rust expect=fire file=src/lib.rs
// frob:tests src/lib.rs::no_such_test
pub fn covered() {}
```

### A target that names a test function is clean

```rust expect=clean file=src/lib.rs
// frob:tests src/lib.rs::covers_it
pub fn covered() {}

#[test]
fn covers_it() {}
```
