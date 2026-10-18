<!-- mdtest: rule=TEST001 -->
# TEST001 tests-target-missing

A `frob:tests` directive must name something the symbol graph can find.

## What it does

On a non-test item the target names a test and must resolve to a test function; inside a test item the target is the symbol the test covers and must resolve to any symbol. A target that resolves to nothing is flagged at the directive.

## Why it matters

A coverage claim that points at nothing is silent: the symbol looks covered while no test is bound to it.

## Remedy

Fix the symref, or remove the directive. A target written `path::Type::method` is not a symref: members nest with `.`, so the finding names the dotted form `path::Type.method` when that resolves.

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

### A `Type::method` target fires with the dotted form as the fix

```rust expect=fire file=src/lib.rs
// frob:tests src/lib.rs::Widget::spin
pub fn covered() {}

pub struct Widget;

impl Widget {
    #[test]
    fn spin() {}
}
```
