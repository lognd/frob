<!-- mdtest: rule=TESTQ001 -->
# TESTQ001 no-assertion

A test that asserts nothing, directly or through a helper in the same file.

## What it does

Fires in Rust, Python, TypeScript/JavaScript and C# test files for a test whose body, and the same-file helpers it calls, hold no assertion (`assert`, `assert_eq!`, `self.assertEqual`, `expect(..)`, `Assert.*`, a `pytest.raises` block and the like). Rust files are scanned wherever `#[test]` appears; other languages only in test files (`test_x.py`, `x.test.ts`, `XTests.cs`, a `tests/` directory). A skipped test is ignored. When the test calls a helper whose body is out of sight (imported from a support module, a base class from another file) the syntax cannot decide, so the finding is Unresolved, never an Error. A code language with no test roles (Go, Java, C, C++) is reported Unresolved once, never clean.

## Why it matters

A test that asserts nothing passes whatever the code does, so it reports coverage it does not provide.

## Remedy

Assert on the result, or on the failure the test expects (`pytest.raises`, `#[should_panic]`).

## Examples

### Fires case 1

```python expect=fire file=tests/test_calc.py
def test_total():
    total = 1 + 2
    print(total)
```

### Fires case 2

```rust expect=fire file=src/lib.rs
#[test]
fn adds() {
    let _sum = 1 + 2;
}
```

### Clean case 3

```python expect=clean file=tests/test_calc.py
def test_total():
    assert 1 + 2 == 3
```

### Clean case 4

```python expect=clean file=tests/test_calc.py
def check(value):
    assert value == 3


def test_total():
    check(1 + 2)
```

### Unresolved case 5

```python expect=unresolved file=tests/test_calc.py
from .support import finish


def test_total():
    finish(1 + 2)
```
