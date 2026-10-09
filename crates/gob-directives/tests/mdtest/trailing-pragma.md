<!-- mdtest: rule=PARSE001 -->
# Trailing foreign pragmas

## Python: noqa after a directive parses cleanly

```python expect=clean
# frob:tests tests/a.py::test_x kind="unit"  # noqa: E501
def test_x():
    pass
```

## Rust: eslint-style pragma after a directive parses cleanly

```rust expect=clean
// frob:invariant name // eslint-disable-line
fn a() {}
```

## Rust: an unrecognised trailing comment is still an extra argument

```rust expect=fire
/* frob:invariant name # nope */ // error: PARSE001
fn a() {}
```
